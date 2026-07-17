/**
 * Hook Runner — bridges Pi runtime events and synthetic extension events to
 * CC-compatible hook scripts.
 *
 * This file is the Pi extension entry point. Module responsibilities:
 * - config.ts    — hooks.json discovery, merge, disable-list, summary
 * - cc-protocol.ts — Claude Code wire-format anti-corruption layer
 * - dispatch.ts  — subprocess execution, matcher evaluation, per-event aggregation
 * - instructions.ts — AGENTS.md / CLAUDE.md / .claude/rules discovery
 * - ui.ts        — /hooks interactive TUI command
 *
 * Hook defaults are loaded from bundled `hooks.json`, then merged with
 * user/project overrides from Pi settings/hooks files.
 * Extensions can invoke synthetic events over cc-hooks:invoke
 * (PermissionRequest, ExitPlanMode, etc).
 */

import type {
	AgentEndEvent,
	BeforeAgentStartEvent,
	BeforeAgentStartEventResult,
	ExtensionAPI,
	ExtensionContext,
	InputEvent,
	InputEventResult,
	SessionBeforeCompactEvent,
	SessionCompactEvent,
	SessionShutdownEvent,
	SessionStartEvent,
	ToolCallEvent,
	ToolCallEventResult,
	ToolResultEvent,
	TurnEndEvent,
} from "@earendil-works/pi-coding-agent";

import { HOOK_RUNNER_INVOKE_CHANNEL, type SyntheticHookInvocationRequest, toCcToolName } from "../shared/hook-bridge.js";
import { decodeGeneric } from "./cc-protocol.js";
import { loadConfig, resolvedConfig, shouldForceReloadForConfigChange } from "./config.js";
import {
	matchingGroups,
	NON_BLOCKING_HOOK_EVENTS,
	parseSlashCommand,
	replaceInput,
	runDecisionHooks,
	runHook,
	runHookAsync,
	runPermissionDeniedGroups,
	runPermissionRequestGroups,
	runPreToolUseGroups,
	serializeToolContent,
} from "./dispatch.js";
import { discoverInstructionFiles } from "./instructions.js";
import { isHookEventName, isRecord } from "./types.js";
import type { HookEventName } from "./types.js";
import { registerHooksCommand } from "./ui.js";

// Re-export the legacy public surface for tests and external callers.
export { _resetForTesting } from "./config.js";
export { matcherMatches, matchingGroups } from "./dispatch.js";
export { toCcToolName } from "../shared/hook-bridge.js";

// ---------------------------------------------------------------------------
// stdin builders
// ---------------------------------------------------------------------------

function baseStdin(hookEventName: HookEventName, ctx: ExtensionContext): Record<string, unknown> {
	return {
		session_id: ctx.sessionManager.getSessionId(),
		cwd: ctx.cwd,
		hook_event_name: hookEventName,
	};
}

function baseStdinFromRecord(hookEventName: HookEventName, stdin: Record<string, unknown>): Record<string, unknown> {
	return {
		session_id: stdin.session_id,
		cwd: stdin.cwd,
		hook_event_name: hookEventName,
	};
}

// ---------------------------------------------------------------------------
// Agent-message delivery — collapses Pi's deliverAs ladder into one helper.
// ---------------------------------------------------------------------------

function sendHookMessageToAgent(pi: ExtensionAPI, ctx: ExtensionContext, text: string): void {
	const payload = text.trim();
	if (!payload) return;
	try {
		if (ctx.isIdle()) {
			pi.sendUserMessage(payload);
			return;
		}
		pi.sendUserMessage(payload, { deliverAs: "steer" });
	} catch {
		try {
			pi.sendUserMessage(payload, { deliverAs: "followUp" });
		} catch {
			ctx.ui.notify(payload, "warning");
		}
	}
}

// ---------------------------------------------------------------------------
// Extension entry
// ---------------------------------------------------------------------------

// Tool-call input cache cap. Sized for sessions that pile up tool calls without
// a matching turn_end (which is when the entries get drained). FIFO eviction
// guarantees the map cannot grow without bound.
const TOOL_INPUT_CACHE_CAP = 1024;

function trackToolInput(map: Map<string, Record<string, unknown>>, callId: string, input: Record<string, unknown>): void {
	if (!map.has(callId) && map.size >= TOOL_INPUT_CACHE_CAP) {
		const oldest = map.keys().next().value;
		if (oldest !== undefined) map.delete(oldest);
	}
	map.set(callId, input);
}

export default function (pi: ExtensionAPI): void {
	let pendingPromptExpansionContext = "";
	let lastHookCwd: string | undefined;
	const toolInputByCallId = new Map<string, Record<string, unknown>>();

	registerHooksCommand(pi);

	// --- extension-to-extension synthetic hook bridge ---
	pi.events.on(HOOK_RUNNER_INVOKE_CHANNEL, (raw) => {
		void (async () => {
			if (!isRecord(raw)) return;
			const req = raw as Partial<SyntheticHookInvocationRequest>;
			if (typeof req.onResult !== "function") return;

			try {
				if (!isRecord(req.stdin)) {
					req.onResult({ blocked: true, reason: "invalid synthetic hook payload" });
					return;
				}
				if (!isHookEventName(req.hookEventName)) {
					req.onResult({ blocked: true, reason: `unsupported synthetic hook event: ${String(req.hookEventName)}` });
					return;
				}

				const hookEventName = req.hookEventName;
				const cwd = typeof req.stdin.cwd === "string" ? req.stdin.cwd : process.cwd();
				let force = false;
				if (hookEventName === "ConfigChange") {
					force = shouldForceReloadForConfigChange();
				}
				loadConfig(cwd, force);

				const withBase = {
					...baseStdinFromRecord(hookEventName, req.stdin),
					...req.stdin,
					hook_event_name: hookEventName,
				};

				if (hookEventName === "PreToolUse") {
					const ccToolName = typeof req.ccToolName === "string" ? req.ccToolName : typeof req.stdin.tool_name === "string" ? req.stdin.tool_name : "";
					const stdin = JSON.stringify({ ...withBase, tool_name: ccToolName });
					const result = await runPreToolUseGroups(resolvedConfig().PreToolUse ?? [], ccToolName, stdin, undefined, req.timeoutSec ?? 10);
					req.onResult(result);
					return;
				}

				if (hookEventName === "PermissionRequest") {
					const ccToolName = typeof req.ccToolName === "string" ? req.ccToolName : typeof req.stdin.tool_name === "string" ? req.stdin.tool_name : "";
					const stdin = JSON.stringify({ ...withBase, tool_name: ccToolName });
					const result = await runPermissionRequestGroups(resolvedConfig().PermissionRequest ?? [], ccToolName, stdin, undefined, req.timeoutSec ?? 10);
					req.onResult(result);
					return;
				}

				if (hookEventName === "PermissionDenied") {
					const ccToolName = typeof req.ccToolName === "string" ? req.ccToolName : typeof req.stdin.tool_name === "string" ? req.stdin.tool_name : "";
					const stdin = JSON.stringify({ ...withBase, tool_name: ccToolName });
					const result = await runPermissionDeniedGroups(resolvedConfig().PermissionDenied ?? [], ccToolName, stdin);
					req.onResult(result);
					return;
				}

				const stdin = JSON.stringify(withBase);
				const groups = resolvedConfig()[hookEventName] ?? [];
				const parsed = await runDecisionHooks(hookEventName, groups, stdin);
				const blocked = NON_BLOCKING_HOOK_EVENTS.has(hookEventName) ? false : parsed.blocked;
				req.onResult({ blocked, reason: parsed.reason, additionalContext: parsed.additionalContext });
			} catch (err) {
				// A throw here (e.g. a circular-reference stdin payload blowing up
				// JSON.stringify) must never leave the caller hanging on its outer
				// wait — up to 30 minutes on the plan-mode ExitPlanMode path. Fail
				// open with the non-blocking default rather than fail-closed: an
				// internal bug in the bridge is not a hook-authored deny decision.
				console.error(`[hook-runner] synthetic hook bridge threw: ${err instanceof Error ? err.stack || err.message : String(err)}`);
				req.onResult({ blocked: false });
			}
		})();
	});

	// --- SessionStart → SessionStart (+ InstructionsLoaded snapshot) ---
	pi.on("session_start", async (event: SessionStartEvent, ctx: ExtensionContext) => {
		if (event.reason === "reload") return;
		loadConfig(ctx.cwd);
		lastHookCwd = ctx.cwd;

		const hookName: HookEventName = "SessionStart";
		const stdin = JSON.stringify({
			...baseStdin(hookName, ctx),
			source: event.reason,
		});

		for (const group of resolvedConfig()[hookName] ?? []) {
			for (const entry of group.hooks) {
				if (entry.config.async) {
					runHookAsync(entry, stdin, (msg, lvl) => ctx.ui.notify(msg, lvl));
					continue;
				}
				const result = await runHook(entry, stdin);
				if (result.exitCode === 0 && result.stdout.trim()) {
					ctx.ui.notify(result.stdout.trim(), "info");
				} else if (result.timedOut) {
					ctx.ui.notify(`Session hook timed out: ${entry.config.command.split("/").at(-1)}`, "error");
				} else if (result.exitCode !== 0) {
					ctx.ui.notify(`Session hook error: ${result.stderr || "non-zero exit"}`, "error");
				}
			}
		}

		const instructionsHookName: HookEventName = "InstructionsLoaded";
		for (const file of discoverInstructionFiles(ctx.cwd)) {
			const fileStdin = JSON.stringify({
				...baseStdin(instructionsHookName, ctx),
				file_path: file.file_path,
				memory_type: file.memory_type,
				load_reason: file.load_reason,
			});
			const groups = matchingGroups(resolvedConfig()[instructionsHookName] ?? [], file.load_reason);
			for (const group of groups) {
				for (const entry of group.hooks) {
					runHookAsync(entry, fileStdin, (msg, lvl) => ctx.ui.notify(msg, lvl));
				}
			}
		}
	});

	// --- session_shutdown → SessionEnd ---
	pi.on("session_shutdown", async (event: SessionShutdownEvent, ctx: ExtensionContext) => {
		const hookName: HookEventName = "SessionEnd";
		const stdin = JSON.stringify({
			...baseStdin(hookName, ctx),
			end_reason: event.reason,
		});
		for (const group of resolvedConfig()[hookName] ?? []) {
			for (const entry of group.hooks) {
				runHookAsync(entry, stdin, (msg, lvl) => ctx.ui.notify(msg, lvl));
			}
		}
	});

	// --- agent_end → Stop / StopFailure + Notification ---
	pi.on("agent_end", async (event: AgentEndEvent, ctx: ExtensionContext) => {
		const lastAssistant = [...event.messages].reverse().find((m) => m.role === "assistant") as
			{ role: "assistant"; stopReason?: string; errorMessage?: string; content?: Array<{ type: string; text?: string }> } | undefined;
		const isFailure = lastAssistant?.stopReason === "error";

		if (isFailure) {
			const hookName: HookEventName = "StopFailure";
			const lastText =
				lastAssistant?.errorMessage ||
				(lastAssistant?.content ?? [])
					.filter((p) => p.type === "text" && typeof p.text === "string")
					.map((p) => p.text)
					.join("\n");
			const failureStdin = JSON.stringify({
				...baseStdin(hookName, ctx),
				error: "unknown",
				error_details: lastAssistant?.errorMessage,
				last_assistant_message: lastText || "",
			});
			for (const group of resolvedConfig()[hookName] ?? []) {
				for (const entry of group.hooks) {
					runHookAsync(entry, failureStdin, (msg, lvl) => ctx.ui.notify(msg, lvl));
				}
			}
		} else {
			const stdin = JSON.stringify(baseStdin("Stop", ctx));
			for (const group of resolvedConfig().Stop ?? []) {
				for (const entry of group.hooks) {
					if (entry.config.async) {
						runHookAsync(entry, stdin, (msg, lvl) => ctx.ui.notify(msg, lvl));
						continue;
					}
					const result = await runHook(entry, stdin);
					if (result.exitCode === 2 && result.stderr.trim()) {
						sendHookMessageToAgent(pi, ctx, result.stderr.trim());
					} else if (result.exitCode !== 0) {
						ctx.ui.notify(`Stop hook error: ${result.stderr}`, "error");
					}
				}
			}
		}

		const notifStdin = JSON.stringify({
			...baseStdin("Notification", ctx),
			title: "Pi",
			message: "Ready for input",
			notification_type: "idle_prompt",
		});
		for (const group of resolvedConfig().Notification ?? []) {
			for (const entry of group.hooks) {
				runHookAsync(entry, notifStdin, (msg, lvl) => ctx.ui.notify(msg, lvl));
			}
		}
	});

	// --- session_before_compact → PreCompact ---
	pi.on("session_before_compact", async (_event: SessionBeforeCompactEvent, ctx: ExtensionContext) => {
		const stdin = JSON.stringify({
			...baseStdin("PreCompact", ctx),
			trigger: "unknown",
		});
		for (const group of resolvedConfig().PreCompact ?? []) {
			for (const entry of group.hooks) {
				const result = await runHook(entry, stdin);
				if (result.exitCode === 2) return { cancel: true };
				if (result.exitCode !== 0) ctx.ui.notify(`PreCompact hook error: ${result.stderr}`, "error");
			}
		}
		return undefined;
	});

	// --- session_compact → PostCompact ---
	pi.on("session_compact", async (event: SessionCompactEvent, ctx: ExtensionContext) => {
		const stdin = JSON.stringify({
			...baseStdin("PostCompact", ctx),
			trigger: event.fromExtension ? "manual" : "auto",
		});
		for (const group of resolvedConfig().PostCompact ?? []) {
			for (const entry of group.hooks) {
				if (entry.config.async) {
					runHookAsync(entry, stdin, (msg, lvl) => ctx.ui.notify(msg, lvl));
					continue;
				}
				const result = await runHook(entry, stdin);
				if (result.exitCode !== 0) ctx.ui.notify(`PostCompact hook error: ${result.stderr}`, "error");
			}
		}
	});

	// --- input → UserPromptExpansion ---
	pi.on("input", async (event: InputEvent, ctx: ExtensionContext): Promise<InputEventResult | undefined> => {
		const parsed = parseSlashCommand(event.text);
		if (!parsed) return undefined;

		const hookName: HookEventName = "UserPromptExpansion";
		const stdin = JSON.stringify({
			...baseStdin(hookName, ctx),
			expansion_type: "slash_command",
			command_name: parsed.commandName,
			command_args: parsed.commandArgs,
			command_source: event.source,
			prompt: parsed.prompt,
		});

		const groups = matchingGroups(resolvedConfig()[hookName] ?? [], parsed.commandName);
		const result = await runDecisionHooks(hookName, groups, stdin, ctx);
		if (result.additionalContext) {
			pendingPromptExpansionContext = [pendingPromptExpansionContext, result.additionalContext].filter(Boolean).join("\n").trim();
		}
		if (result.blocked) {
			ctx.ui.notify(result.reason ?? "Command expansion blocked by hook", "warning");
			return { action: "handled" };
		}
		return undefined;
	});

	// --- before_agent_start → CwdChanged + UserPromptSubmit ---
	pi.on("before_agent_start", async (event: BeforeAgentStartEvent, ctx: ExtensionContext): Promise<BeforeAgentStartEventResult | undefined> => {
		if (lastHookCwd && lastHookCwd !== ctx.cwd) {
			loadConfig(ctx.cwd);
			const cwdHookName: HookEventName = "CwdChanged";
			const cwdStdin = JSON.stringify({
				...baseStdin(cwdHookName, ctx),
				old_cwd: lastHookCwd,
				new_cwd: ctx.cwd,
			});
			const cwdResult = await runDecisionHooks(cwdHookName, resolvedConfig()[cwdHookName] ?? [], cwdStdin, ctx);
			if (cwdResult.additionalContext) {
				sendHookMessageToAgent(pi, ctx, cwdResult.additionalContext);
			}
		}
		lastHookCwd = ctx.cwd;

		const stdin = JSON.stringify({
			...baseStdin("UserPromptSubmit", ctx),
			prompt: event.prompt,
		});

		let injected = "";
		for (const group of resolvedConfig().UserPromptSubmit ?? []) {
			for (const entry of group.hooks) {
				const result = await runHook(entry, stdin, 15);
				if (result.exitCode === 2 && result.stderr.trim()) {
					injected += result.stderr.trim() + "\n";
				} else if (result.exitCode === 0 && result.stdout.trim()) {
					injected += result.stdout.trim() + "\n";
				} else if (result.exitCode !== 0) {
					ctx.ui.notify(`Prompt hook error: ${result.stderr}`, "error");
				}
			}
		}

		if (pendingPromptExpansionContext.trim()) {
			injected += pendingPromptExpansionContext.trim() + "\n";
			pendingPromptExpansionContext = "";
		}

		if (!injected.trim()) return undefined;
		const text = injected.trim();
		return {
			message: {
				customType: "hook-context",
				content: [{ type: "text", text }],
				display: true,
			},
		};
	});

	// --- tool_call → PreToolUse ---
	pi.on("tool_call", async (event: ToolCallEvent, ctx: ExtensionContext): Promise<ToolCallEventResult | undefined> => {
		const ccName = toCcToolName(event.toolName);
		const stdin = JSON.stringify({
			...baseStdin("PreToolUse", ctx),
			tool_name: ccName,
			tool_input: event.input,
			tool_use_id: event.toolCallId,
		});

		const result = await runPreToolUseGroups(resolvedConfig().PreToolUse ?? [], ccName, stdin, ctx, 10);
		if (result.updatedInput) {
			if (!isRecord(event.input)) {
				return { block: true, reason: "Hook updatedInput rejected: tool input is not a mutable object" };
			}
			replaceInput(event.input, result.updatedInput);
		}
		if (result.blocked) {
			return { block: true, reason: result.reason || "Blocked by hook" };
		}
		if (isRecord(event.input)) {
			trackToolInput(toolInputByCallId, event.toolCallId, structuredClone(event.input));
		}
		return undefined;
	});

	// --- tool_result → PostToolUse / PostToolUseFailure ---
	pi.on("tool_result", async (event: ToolResultEvent, ctx: ExtensionContext) => {
		const ccName = toCcToolName(event.toolName);
		const hookName: HookEventName = event.isError ? "PostToolUseFailure" : "PostToolUse";
		if (isRecord(event.input) && !toolInputByCallId.has(event.toolCallId)) {
			trackToolInput(toolInputByCallId, event.toolCallId, structuredClone(event.input));
		}
		const stdin = JSON.stringify({
			...baseStdin(hookName, ctx),
			tool_name: ccName,
			tool_input: event.input,
			tool_use_id: event.toolCallId,
			...(event.isError
				? { error: "tool execution failed" }
				: {
						tool_response: event.content
							.filter((c): c is { type: "text"; text: string } => c.type === "text")
							.map((c) => c.text)
							.join("\n"),
					}),
		});

		const groups = matchingGroups(resolvedConfig()[hookName] ?? [], ccName);
		const feedbackLines: string[] = [];
		const extraContexts: string[] = [];

		for (const group of groups) {
			for (const entry of group.hooks) {
				if (entry.config.async) {
					runHookAsync(entry, stdin, (msg, lvl) => ctx.ui.notify(msg, lvl), entry.config.timeout ?? 120);
					continue;
				}
				const result = await runHook(entry, stdin, entry.config.timeout ?? 60);
				if (result.exitCode === 2 && result.stderr.trim()) {
					feedbackLines.push(result.stderr.trim());
					continue;
				}
				if (result.exitCode !== 0) {
					ctx.ui.notify(`Post-tool hook error (${entry.config.command.split("/").at(-1)}): ${result.stderr}`, "error");
					continue;
				}
				const parsed = decodeGeneric(result.stdout, hookName);
				if (parsed.block && parsed.reason) {
					feedbackLines.push(parsed.reason);
				}
				if (parsed.additionalContext) {
					extraContexts.push(parsed.additionalContext);
				}
			}
		}

		if (feedbackLines.length === 0 && extraContexts.length === 0) return undefined;
		const appended: Array<{ type: "text"; text: string }> = [];
		if (feedbackLines.length > 0) {
			appended.push({ type: "text", text: "⚠️ Hook output:\n" + feedbackLines.join("\n---\n") });
		}
		if (extraContexts.length > 0) {
			appended.push({ type: "text", text: extraContexts.join("\n") });
		}
		return {
			content: [...event.content, ...appended],
		};
	});

	// --- turn_end → PostToolBatch ---
	pi.on("turn_end", async (event: TurnEndEvent, ctx: ExtensionContext) => {
		if (!event.toolResults || event.toolResults.length === 0) return;
		const hookName: HookEventName = "PostToolBatch";
		const toolCalls = event.toolResults.map((result) => ({
			tool_name: toCcToolName(result.toolName),
			tool_input: toolInputByCallId.get(result.toolCallId) ?? {},
			tool_use_id: result.toolCallId,
			tool_response: serializeToolContent(result.content as Array<{ type: string; text?: string }>),
			is_error: result.isError,
		}));
		for (const result of event.toolResults) {
			toolInputByCallId.delete(result.toolCallId);
		}
		const stdin = JSON.stringify({
			...baseStdin(hookName, ctx),
			tool_calls: toolCalls,
		});
		const result = await runDecisionHooks(hookName, resolvedConfig()[hookName] ?? [], stdin, ctx);
		if (result.additionalContext) {
			sendHookMessageToAgent(pi, ctx, result.additionalContext);
		}
		if (result.blocked && result.reason) {
			sendHookMessageToAgent(pi, ctx, result.reason);
		}
	});
}
