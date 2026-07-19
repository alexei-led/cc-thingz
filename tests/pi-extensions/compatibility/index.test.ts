import { beforeEach, describe, expect, it, mock } from "bun:test";

import type { ExtensionAPI, ExtensionContext } from "@earendil-works/pi-coding-agent";
import { HOOK_RUNNER_INVOKE_CHANNEL, type SyntheticHookInvocationResult } from "../../../src/plugins/pi/extensions/extensions/shared/hook-bridge.js";

// ---------------------------------------------------------------------------
// Controllable invokeSyntheticHook mock — defaults to the real bus-routing
// implementation so existing tests that wire busHandlers work unchanged.
// Individual tests can override invokeHookImpl to inject synthetic results.
// ---------------------------------------------------------------------------

type InvokeHookFn = (
	pi: ExtensionAPI,
	ctx: ExtensionContext,
	request: {
		hookEventName: string;
		stdin: Record<string, unknown>;
		ccToolName?: string;
		timeoutMs?: number;
		timeoutResult?: SyntheticHookInvocationResult;
	},
) => Promise<SyntheticHookInvocationResult>;

let invokeHookImpl: InvokeHookFn = async (pi, _ctx, request) => {
	// Real bus-routing: emit on HOOK_RUNNER_INVOKE_CHANNEL and wait for onResult.
	// This is the same logic as the real invokeSyntheticHook, minus outer timeout,
	// so existing busHandlers-based tests work without change.
	return await new Promise((resolve) => {
		pi.events.emit(HOOK_RUNNER_INVOKE_CHANNEL, {
			hookEventName: request.hookEventName,
			ccToolName: request.ccToolName,
			stdin: request.stdin,
			onResult: resolve,
		});
	});
};

mock.module("../../../src/plugins/pi/extensions/extensions/shared/hook-bridge.js", () => ({
	HOOK_RUNNER_INVOKE_CHANNEL,
	invokeSyntheticHook: (pi: ExtensionAPI, ctx: ExtensionContext, request: Parameters<InvokeHookFn>[2]) => invokeHookImpl(pi, ctx, request),
}));

mock.module("@earendil-works/pi-agent-core", () => ({}));
mock.module("@earendil-works/pi-ai", () => ({}));
mock.module("@earendil-works/pi-coding-agent", () => ({}));
mock.module("@earendil-works/pi-tui", () => ({
	Key: {
		ctrlAlt: (_key: string) => "ctrl-alt",
	},
}));

const { default: planModeExtension } = await import("../../../src/plugins/pi/extensions/extensions/plan-mode/index.ts");

type EventHandler = (...args: any[]) => Promise<any> | any;

type Command = { handler: (args: string[], ctx: any) => Promise<void> | void };

function makePi() {
	const handlers = new Map<string, EventHandler>();
	const commands = new Map<string, Command>();
	const busHandlers = new Map<string, (payload: unknown) => void>();
	let activeTools = ["read", "bash", "ask_user_question", "write", "edit"];

	const pi = {
		on: (event: string, handler: EventHandler) => handlers.set(event, handler),
		registerCommand: (name: string, command: Command) => commands.set(name, command),
		registerShortcut: mock(() => {}),
		registerFlag: mock(() => {}),
		appendEntry: mock(() => {}),
		sendMessage: mock(() => {}),
		sendUserMessage: mock(() => {}),
		getAllTools: () => activeTools.map((name) => ({ name })),
		getActiveTools: () => [...activeTools],
		setActiveTools: (tools: string[]) => {
			activeTools = [...tools];
		},
		getFlag: (_name: string) => undefined,
		events: {
			on: (channel: string, handler: (payload: unknown) => void) => {
				busHandlers.set(channel, handler);
				return () => busHandlers.delete(channel);
			},
			emit: (channel: string, payload: unknown) => {
				const handler = busHandlers.get(channel);
				handler?.(payload);
			},
		},
	};

	planModeExtension(pi as any);

	return { pi, handlers, commands, busHandlers, getActiveTools: () => activeTools };
}

function makeCtx(selectResults: Array<string | undefined> = []) {
	return {
		hasUI: true,
		cwd: "/workspace",
		sessionManager: {
			getSessionId: () => "sess-test",
			getEntries: () => [],
		},
		ui: {
			notify: mock(() => {}),
			select: mock(async () => selectResults.shift()),
			editor: mock(async () => ""),
			setStatus: mock(() => {}),
			setWidget: mock(() => {}),
			theme: {
				fg: (_tone: string, text: string) => text,
				strikethrough: (text: string) => text,
			},
		},
	};
}

const PLAN_WITH_STEPS = `Plan:
1. Read the config file
2. Apply the changes`;

describe("plan-mode / ExitPlanMode hardening", () => {
	beforeEach(() => {
		mock.restore();
	});

	it("allows execute path when no Plan content exists and no hook listener (fail-open)", async () => {
		const { pi, handlers, commands, busHandlers, getActiveTools } = makePi();
		const ctx = makeCtx(["Execute the plan"]);

		// Synthetic hook responder returns {} → blocked=false, fail-open path
		busHandlers.set(HOOK_RUNNER_INVOKE_CHANNEL, (raw: unknown) => {
			const req = raw as { onResult?: (r: Record<string, unknown>) => void };
			req.onResult?.({});
		});

		await commands.get("plan")!.handler([], ctx);
		await handlers.get("agent_end")!({ messages: [] }, ctx);

		expect(ctx.ui.notify).not.toHaveBeenCalledWith(expect.stringContaining("blocked"), "warning");
		expect(pi.sendMessage).toHaveBeenCalledWith(expect.objectContaining({ customType: "plan-mode-execute" }), expect.objectContaining({ triggerTurn: true }));
		expect(getActiveTools()).toContain("write");
	});

	it("blocks execute path for invalid bash tool input while plan mode is active", async () => {
		const { commands, handlers } = makePi();
		const ctx = makeCtx();
		await commands.get("plan")!.handler([], ctx);

		const result = await handlers.get("tool_call")!({ toolName: "bash", input: { command: 123 } }, ctx);
		expect(result).toEqual({ block: true, reason: "Plan mode: invalid bash command input." });
	});

	it("registers its todo list command as /plan-todos, not /todos (todo.ts owns /todos)", async () => {
		const { commands } = makePi();
		const ctx = makeCtx();

		expect(commands.has("plan-todos")).toBe(true);
		expect(commands.has("todos")).toBe(false);

		await commands.get("plan-todos")!.handler([], ctx);
		expect(ctx.ui.notify).toHaveBeenCalledWith("No todos. Create a plan first with /plan", "info");
	});
});

describe("plan-mode / ExitPlanMode hook integration", () => {
	beforeEach(() => {
		mock.restore();
	});

	// Helper: drive agent_end through one full "Execute the plan" flow with a
	// pre-wired hook responder on the HOOK_RUNNER_INVOKE_CHANNEL bus.
	async function runAgentEndWithHook(hookResult: Record<string, unknown>, planText = PLAN_WITH_STEPS) {
		const { pi, handlers, commands, busHandlers, getActiveTools } = makePi();
		const ctx = makeCtx(["Execute the plan (track progress)"]);

		// Enable plan mode
		await commands.get("plan")!.handler([], ctx);

		// Register a synthetic hook responder BEFORE agent_end fires
		busHandlers.set(HOOK_RUNNER_INVOKE_CHANNEL, (raw: unknown) => {
			const req = raw as { onResult?: (r: Record<string, unknown>) => void };
			req.onResult?.(hookResult);
		});

		// Feed a last assistant message that contains a plan
		const lastMessage = {
			role: "assistant",
			content: [{ type: "text", text: planText }],
		};
		await handlers.get("agent_end")!({ messages: [lastMessage] }, ctx);

		return { pi, ctx, getActiveTools };
	}

	it("allows execution when hook returns allow (no updatedPlan)", async () => {
		const { pi, ctx, getActiveTools } = await runAgentEndWithHook({ blocked: false });

		// planModeEnabled false → execution starts, tools restored to full set
		expect(getActiveTools()).toContain("write");
		expect(ctx.ui.notify).not.toHaveBeenCalledWith(expect.stringContaining("blocked"), expect.any(String));
		expect(pi.sendMessage).toHaveBeenCalledWith(expect.objectContaining({ customType: "plan-mode-execute" }), expect.objectContaining({ triggerTurn: true }));
	});

	it("keeps plan mode active when a non-revdiff hook asks for clarification", async () => {
		const { pi, getActiveTools } = await runAgentEndWithHook({
			blocked: true,
			decision: "ask",
			reason: "Confirm the rollout window",
		});

		expect(getActiveTools()).toEqual(["read", "bash", "ask_user_question"]);
		expect(pi.sendUserMessage).toHaveBeenCalledWith("Confirm the rollout window");
		expect(pi.sendMessage).not.toHaveBeenCalledWith(expect.objectContaining({ customType: "plan-mode-execute" }), expect.any(Object));
	});

	it("preserves the previous-revision marker in the next hook input", async () => {
		const { pi, handlers, commands, busHandlers } = makePi();
		const ctx = makeCtx(["Execute the plan (track progress)"]);
		const revisedPlan = `<!-- previous revision: /tmp/plan-rev-abc.md -->\n${PLAN_WITH_STEPS}`;
		let capturedPlan = "";

		await commands.get("plan")!.handler([], ctx);
		busHandlers.set(HOOK_RUNNER_INVOKE_CHANNEL, (raw: unknown) => {
			const req = raw as {
				stdin: { tool_input: { plan: string } };
				onResult?: (result: Record<string, unknown>) => void;
			};
			capturedPlan = req.stdin.tool_input.plan;
			req.onResult?.({ blocked: false });
		});

		await handlers.get("agent_end")!(
			{
				messages: [{ role: "assistant", content: [{ type: "text", text: revisedPlan }] }],
			},
			ctx,
		);

		expect(capturedPlan).toBe(revisedPlan);
		expect(pi.sendMessage).toHaveBeenCalledWith(expect.objectContaining({ customType: "plan-mode-execute" }), expect.objectContaining({ triggerTurn: true }));
	});

	it("blocks execution and notifies when hook returns blocked with reason", async () => {
		const { pi, ctx, getActiveTools } = await runAgentEndWithHook({
			blocked: true,
			reason: "Plan has unresolved risks",
		});

		expect(ctx.ui.notify).toHaveBeenCalledWith("Plan has unresolved risks", "warning");
		expect(pi.sendUserMessage).toHaveBeenCalledWith("Plan has unresolved risks");
		// Plan mode stays active; tools remain restricted
		expect(getActiveTools()).toEqual(["read", "bash", "ask_user_question"]);
		// sendMessage with triggerTurn must NOT have been called
		expect(pi.sendMessage).not.toHaveBeenCalledWith(expect.objectContaining({ customType: "plan-mode-execute" }), expect.any(Object));
	});

	it("rebuilds todoItems from updatedPlan returned by hook", async () => {
		const updatedPlan = `Plan:\n1. Revised step A\n2. Revised step B\n3. Revised step C`;
		const { pi } = await runAgentEndWithHook({
			blocked: false,
			updatedInput: { plan: updatedPlan },
		});

		// The exec message should reference the first step from the updated plan
		expect(pi.sendMessage).toHaveBeenCalledWith(
			expect.objectContaining({
				customType: "plan-mode-execute",
				content: expect.stringContaining("Revised step A"),
			}),
			expect.any(Object),
		);
	});

	it("appends additionalContext from hook to the execution message", async () => {
		const { pi } = await runAgentEndWithHook({
			blocked: false,
			additionalContext: "Review annotations: line 42 needs a guard",
		});

		expect(pi.sendMessage).toHaveBeenCalledWith(
			expect.objectContaining({
				content: expect.stringContaining("Review annotations: line 42 needs a guard"),
			}),
			expect.any(Object),
		);
	});

	it("blocks execution when hook-runner returns an explicit blocked decision", async () => {
		// Hook-runner delivers an explicit blocked verdict (e.g., a per-entry
		// timeout that fired inside the runner). The outer-wait timeout path is
		// exercised separately in the describe block below.
		const { pi, ctx, getActiveTools } = await runAgentEndWithHook({
			blocked: true,
			reason: "Plan exit review timed out.",
		});

		expect(ctx.ui.notify).toHaveBeenCalledWith("Plan exit review timed out.", "warning");
		expect(pi.sendUserMessage).toHaveBeenCalledWith("Plan exit review timed out.");
		expect(getActiveTools()).toEqual(["read", "bash", "ask_user_question"]);
	});
});

describe("plan-mode / ExitPlanMode outer-wait timeout (fail-closed)", () => {
	const savedImpl = invokeHookImpl;

	beforeEach(() => {
		mock.restore();
		invokeHookImpl = savedImpl;
	});

	it("blocks execution and stays in plan mode when outer-wait timeout fires", async () => {
		// Simulate the 30-minute outer-wait timer firing by making invokeSyntheticHook
		// return the timeoutResult directly — the same value plan-mode passes to it.
		// This tests plan-mode's response to the timeout, not the timer mechanism itself.
		invokeHookImpl = async (_pi, _ctx, request) => request.timeoutResult ?? {};

		const { pi, handlers, commands, getActiveTools } = makePi();
		const ctx = makeCtx(["Execute the plan (track progress)"]);
		await commands.get("plan")!.handler([], ctx);

		const lastMessage = {
			role: "assistant",
			content: [{ type: "text", text: PLAN_WITH_STEPS }],
		};
		await handlers.get("agent_end")!({ messages: [lastMessage] }, ctx);

		expect(ctx.ui.notify).toHaveBeenCalledWith("Plan exit review timed out.", "warning");
		expect(pi.sendUserMessage).toHaveBeenCalledWith("Plan exit review timed out.");
		expect(getActiveTools()).toEqual(["read", "bash", "ask_user_question"]);
		expect(pi.sendMessage).not.toHaveBeenCalledWith(expect.objectContaining({ customType: "plan-mode-execute" }), expect.any(Object));
	});
});
