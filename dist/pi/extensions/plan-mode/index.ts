/**
 * Plan Mode Extension
 *
 * Read-only exploration mode for safe code analysis.
 * When enabled, only read-only tools are available.
 *
 * Features:
 * - /plan command or Ctrl+Alt+P to toggle
 * - Bash restricted to allowlisted read-only commands
 * - Extracts numbered plan steps from "Plan:" sections
 * - ExitPlanMode synthetic PreToolUse review before execution starts
 * - [DONE:n] markers to complete steps during execution
 * - Progress tracking widget during execution
 */

import type { AgentMessage } from "@earendil-works/pi-agent-core";
import type { AssistantMessage, TextContent } from "@earendil-works/pi-ai";
import type { ExtensionAPI, ExtensionContext } from "@earendil-works/pi-coding-agent";
import { Key } from "@earendil-works/pi-tui";
import { invokeSyntheticHook, toCcToolName } from "../shared/hook-bridge.js";
import { extractTodoItems, isSafeCommand, markCompletedSteps, type TodoItem } from "./utils.js";

// Tools
const PLAN_MODE_TOOL_CANDIDATES = ["read", "bash", "ask_user_question"];

// Type guard for assistant messages
function isAssistantMessage(m: AgentMessage): m is AssistantMessage {
	return m.role === "assistant" && Array.isArray(m.content);
}

// Extract text content from an assistant message
function getTextContent(message: AssistantMessage): string {
	return message.content
		.filter((block): block is TextContent => block.type === "text")
		.map((block) => block.text)
		.join("\n");
}

function extractPlanMarkdown(message: string): string {
	const header = message.match(/\*{0,2}Plan:\*{0,2}\s*\n/i);
	if (!header || header.index === undefined) return "";
	return message.slice(header.index).trim();
}

function buildPlanMarkdownFromTodos(items: TodoItem[]): string {
	if (items.length === 0) return "";
	const lines = ["Plan:"];
	for (const item of items) {
		lines.push(`${item.step}. ${item.text}`);
	}
	return lines.join("\n");
}

export default function planModeExtension(pi: ExtensionAPI): void {
	let planModeEnabled = false;
	let executionMode = false;
	let todoItems: TodoItem[] = [];
	let normalModeTools: string[] = [];
	let latestPlanMarkdown = "";
	let planExitAttempt = 0;

	function getPlanModeTools(): string[] {
		const available = new Set(pi.getAllTools().map((tool) => tool.name));
		return PLAN_MODE_TOOL_CANDIDATES.filter((name) => available.has(name));
	}

	function restoreNormalTools(): void {
		if (normalModeTools.length > 0) {
			pi.setActiveTools(normalModeTools);
			return;
		}
		pi.setActiveTools(pi.getAllTools().map((tool) => tool.name));
	}

	pi.registerFlag("plan", {
		description: "Start in plan mode (read-only exploration)",
		type: "boolean",
		default: false,
	});

	function updateStatus(ctx: ExtensionContext): void {
		// Footer status
		if (executionMode && todoItems.length > 0) {
			const completed = todoItems.filter((t) => t.completed).length;
			ctx.ui.setStatus("plan-mode", ctx.ui.theme.fg("accent", `📋 ${completed}/${todoItems.length}`));
		} else if (planModeEnabled) {
			ctx.ui.setStatus("plan-mode", ctx.ui.theme.fg("warning", "⏸ plan"));
		} else {
			ctx.ui.setStatus("plan-mode", undefined);
		}

		// Widget showing todo list
		if (executionMode && todoItems.length > 0) {
			const lines = todoItems.map((item) => {
				if (item.completed) {
					return ctx.ui.theme.fg("success", "☑ ") + ctx.ui.theme.fg("muted", ctx.ui.theme.strikethrough(item.text));
				}
				return `${ctx.ui.theme.fg("muted", "☐ ")}${item.text}`;
			});
			ctx.ui.setWidget("plan-todos", lines);
		} else {
			ctx.ui.setWidget("plan-todos", undefined);
		}
	}

	function togglePlanMode(ctx: ExtensionContext): void {
		planModeEnabled = !planModeEnabled;
		executionMode = false;
		todoItems = [];
		latestPlanMarkdown = "";
		planExitAttempt = 0;

		if (planModeEnabled) {
			normalModeTools = pi.getActiveTools();
			const planTools = getPlanModeTools();
			pi.setActiveTools(planTools);
			ctx.ui.notify(`Plan mode enabled. Tools: ${planTools.join(", ")}`);
		} else {
			restoreNormalTools();
			ctx.ui.notify("Plan mode disabled. Full access restored.");
		}
		updateStatus(ctx);
	}

	function persistState(): void {
		pi.appendEntry("plan-mode", {
			enabled: planModeEnabled,
			todos: todoItems,
			executing: executionMode,
		});
	}

	async function invokeExitPlanHook(
		ctx: ExtensionContext,
		planMarkdown: string,
	): Promise<{ blocked: boolean; reason?: string; updatedPlan?: string; additionalContext?: string }> {
		const sessionId = ctx.sessionManager.getSessionId();
		if (typeof sessionId !== "string") {
			return { blocked: false };
		}
		// Fail-open on empty plan content: no plan means there is nothing for the
		// review hook to inspect, so skip the hook rather than send `plan: ""`.
		if (!planMarkdown.trim()) {
			return { blocked: false };
		}
		const toolUseId = `plan-exit-${Date.now()}-${++planExitAttempt}`;
		const exitPlanMode = toCcToolName("exit_plan_mode");
		const stdin = {
			session_id: sessionId,
			cwd: ctx.cwd,
			hook_event_name: "PreToolUse",
			tool_name: exitPlanMode,
			tool_use_id: toolUseId,
			tool_input: {
				plan: planMarkdown,
				planFilePath: "",
				allowedPrompts: [],
			},
		};
		// ExitPlanMode review can be interactive (e.g., revdiff annotation by the user).
		// Outer wait set to 30 minutes; per-entry `timeout` in hooks.json must fire
		// first so hook-runner returns a blocked deny instead of the outer wait
		// firing here. If the outer wait does fire, treat it as blocking: a stuck
		// hook-runner is a malfunction, not an approval.
		const result = await invokeSyntheticHook(pi, ctx, {
			hookEventName: "PreToolUse",
			ccToolName: exitPlanMode,
			stdin,
			timeoutMs: 30 * 60 * 1000,
			enforceFloor: true,
			timeoutResult: { blocked: true, reason: "Plan exit review timed out." },
		});
		const updatedPlan = result.updatedInput && typeof result.updatedInput.plan === "string" ? result.updatedInput.plan : undefined;

		if (result.decision === "ask") {
			const question = (result.reason ?? "").trim() || "ExitPlanMode review needs clarification before the plan can run.";
			const askContext = [
				question,
				"Use the `ask_user_question` tool to surface this to the user, then re-issue the plan once you have an answer.",
				result.additionalContext?.trim() ? result.additionalContext.trim() : "",
			]
				.filter(Boolean)
				.join("\n\n");
			return { blocked: true, reason: question, updatedPlan, additionalContext: askContext };
		}

		return {
			blocked: result.blocked === true,
			reason: result.reason,
			updatedPlan,
			additionalContext: result.additionalContext,
		};
	}

	pi.registerCommand("plan", {
		description: "Toggle plan mode (read-only exploration)",
		handler: async (_args, ctx) => togglePlanMode(ctx),
	});

	pi.registerCommand("plan-todos", {
		description: "Show current plan todo list",
		handler: async (_args, ctx) => {
			if (todoItems.length === 0) {
				ctx.ui.notify("No todos. Create a plan first with /plan", "info");
				return;
			}
			const list = todoItems.map((item, i) => `${i + 1}. ${item.completed ? "✓" : "○"} ${item.text}`).join("\n");
			ctx.ui.notify(`Plan Progress:\n${list}`, "info");
		},
	});

	pi.registerShortcut(Key.ctrlAlt("p"), {
		description: "Toggle plan mode",
		handler: async (ctx) => togglePlanMode(ctx),
	});

	// Block destructive bash commands in plan mode
	pi.on("tool_call", async (event) => {
		if (!planModeEnabled || event.toolName !== "bash") return;

		const commandRaw = event.input.command;
		if (typeof commandRaw !== "string" || commandRaw.trim() === "") {
			return {
				block: true,
				reason: "Plan mode: invalid bash command input.",
			};
		}

		if (!isSafeCommand(commandRaw)) {
			return {
				block: true,
				reason: `Plan mode: command blocked (not allowlisted). Use /plan to disable plan mode first.\nCommand: ${commandRaw}`,
			};
		}
	});

	// Filter out stale plan mode context when not in plan mode
	pi.on("context", async (event) => {
		if (planModeEnabled) return;

		return {
			messages: event.messages.filter((m) => {
				const msg = m as AgentMessage & { customType?: string };
				if (msg.customType === "plan-mode-context") return false;
				if (msg.role !== "user") return true;

				const content = msg.content;
				if (typeof content === "string") {
					return !content.includes("[PLAN MODE ACTIVE]");
				}
				if (Array.isArray(content)) {
					return !content.some((c) => c.type === "text" && (c as TextContent).text?.includes("[PLAN MODE ACTIVE]"));
				}
				return true;
			}),
		};
	});

	// Inject plan/execution context before agent starts
	pi.on("before_agent_start", async () => {
		if (planModeEnabled) {
			return {
				message: {
					customType: "plan-mode-context",
					content: `[PLAN MODE ACTIVE]
You are in plan mode - a read-only exploration mode for safe code analysis.

Restrictions:
- You can only use: read, bash, ask_user_question
- You CANNOT use: edit, write (file modifications are disabled)
- Bash is restricted to an allowlist of read-only commands

Ask clarifying questions using the ask_user_question tool.
Use bash only for read-only project inspection.

Create a detailed numbered plan under a "Plan:" header:

Plan:
1. First step description
2. Second step description
...

Do NOT attempt to make changes - just describe what you would do.`,
					display: false,
				},
			};
		}

		if (executionMode && todoItems.length > 0) {
			const remaining = todoItems.filter((t) => !t.completed);
			const todoList = remaining.map((t) => `${t.step}. ${t.text}`).join("\n");
			return {
				message: {
					customType: "plan-execution-context",
					content: `[EXECUTING PLAN - Full tool access enabled]

Remaining steps:
${todoList}

Execute each step in order.
After completing a step, include a [DONE:n] tag in your response.`,
					display: false,
				},
			};
		}
	});

	// Track progress after each turn
	pi.on("turn_end", async (event, ctx) => {
		if (!executionMode || todoItems.length === 0) return;
		if (!isAssistantMessage(event.message)) return;

		const text = getTextContent(event.message);
		if (markCompletedSteps(text, todoItems) > 0) {
			updateStatus(ctx);
		}
		persistState();
	});

	// Handle plan completion and plan mode UI
	pi.on("agent_end", async (event, ctx) => {
		// Check if execution is complete
		if (executionMode && todoItems.length > 0) {
			if (todoItems.every((t) => t.completed)) {
				const completedList = todoItems.map((t) => `~~${t.text}~~`).join("\n");
				pi.sendMessage({ customType: "plan-complete", content: `**Plan Complete!** ✓\n\n${completedList}`, display: true }, { triggerTurn: false });
				executionMode = false;
				todoItems = [];
				latestPlanMarkdown = "";
				restoreNormalTools();
				updateStatus(ctx);
				persistState(); // Save cleared state so resume doesn't restore old execution mode
			}
			return;
		}

		if (!planModeEnabled || !ctx.hasUI) return;

		// Extract todos from last assistant message
		const lastAssistant = [...event.messages].reverse().find(isAssistantMessage);
		if (lastAssistant) {
			const text = getTextContent(lastAssistant);
			const extracted = extractTodoItems(text);
			if (extracted.length > 0) {
				todoItems = extracted;
			}
			const planMarkdown = extractPlanMarkdown(text);
			if (planMarkdown) {
				latestPlanMarkdown = planMarkdown;
			}
		}

		// Show plan steps and prompt for next action
		if (todoItems.length > 0) {
			const todoListText = todoItems.map((t, i) => `${i + 1}. ☐ ${t.text}`).join("\n");
			pi.sendMessage(
				{
					customType: "plan-todo-list",
					content: `**Plan Steps (${todoItems.length}):**\n\n${todoListText}`,
					display: true,
				},
				{ triggerTurn: false },
			);
		}

		const choice = await ctx.ui.select("Plan mode - what next?", [
			todoItems.length > 0 ? "Execute the plan (track progress)" : "Execute the plan",
			"Stay in plan mode",
			"Refine the plan",
		]);

		if (choice?.startsWith("Execute")) {
			const currentPlan = latestPlanMarkdown || buildPlanMarkdownFromTodos(todoItems);
			const hookResult = await invokeExitPlanHook(ctx, currentPlan);
			if (hookResult.updatedPlan) {
				latestPlanMarkdown = hookResult.updatedPlan;
				const extracted = extractTodoItems(hookResult.updatedPlan);
				if (extracted.length > 0) {
					todoItems = extracted;
				}
			}
			if (hookResult.blocked) {
				const reason = hookResult.reason?.trim() || "Plan exit blocked by hook.";
				ctx.ui.notify(reason, "warning");
				persistState();
				pi.sendUserMessage(reason);
				return;
			}

			planModeEnabled = false;
			executionMode = todoItems.length > 0;
			restoreNormalTools();
			updateStatus(ctx);

			const contextSuffix = hookResult.additionalContext?.trim() ? `\n\n${hookResult.additionalContext.trim()}` : "";
			const execMessage =
				todoItems.length > 0 ? `Execute the plan. Start with: ${todoItems[0].text}${contextSuffix}` : `Execute the plan you just created.${contextSuffix}`;
			pi.sendMessage({ customType: "plan-mode-execute", content: execMessage, display: true }, { triggerTurn: true });
		} else if (choice === "Refine the plan") {
			const refinement = await ctx.ui.editor("Refine the plan:", "");
			if (refinement?.trim()) {
				pi.sendUserMessage(refinement.trim());
			}
		}
	});

	// Restore state on session start/resume
	pi.on("session_start", async (_event, ctx) => {
		if (pi.getFlag("plan") === true) {
			planModeEnabled = true;
		}

		const entries = ctx.sessionManager.getEntries();

		// Restore persisted state
		const planModeEntry = entries.filter((e: { type: string; customType?: string }) => e.type === "custom" && e.customType === "plan-mode").pop() as
			{ data?: { enabled: boolean; todos?: TodoItem[]; executing?: boolean } } | undefined;

		if (planModeEntry?.data) {
			planModeEnabled = planModeEntry.data.enabled ?? planModeEnabled;
			todoItems = planModeEntry.data.todos ?? todoItems;
			executionMode = planModeEntry.data.executing ?? executionMode;
		}

		// On resume: re-scan messages to rebuild completion state
		// Only scan messages AFTER the last "plan-mode-execute" to avoid picking up [DONE:n] from previous plans
		const isResume = planModeEntry !== undefined;
		if (isResume && executionMode && todoItems.length > 0) {
			// Find the index of the last plan-mode-execute entry (marks when current execution started)
			let executeIndex = -1;
			for (let i = entries.length - 1; i >= 0; i--) {
				const entry = entries[i] as { type: string; customType?: string };
				if (entry.customType === "plan-mode-execute") {
					executeIndex = i;
					break;
				}
			}

			// Only scan messages after the execute marker
			const messages: AssistantMessage[] = [];
			for (let i = executeIndex + 1; i < entries.length; i++) {
				const entry = entries[i];
				if (entry.type === "message" && "message" in entry && isAssistantMessage(entry.message as AgentMessage)) {
					messages.push(entry.message as AssistantMessage);
				}
			}
			const allText = messages.map(getTextContent).join("\n");
			markCompletedSteps(allText, todoItems);
		}

		if (planModeEnabled) {
			const activeTools = pi.getActiveTools();
			normalModeTools = activeTools.length > 0 ? activeTools : pi.getAllTools().map((tool) => tool.name);
			pi.setActiveTools(getPlanModeTools());
		}
		updateStatus(ctx);
	});
}
