/**
 * Hook execution and per-event dispatch.
 *
 * Dispatchers consume decoded decisions from cc-protocol and apply
 * aggregation rules: PreToolUse decision-rank, PermissionRequest first-deny-wins,
 * generic block/context accumulation. Subprocess execution and matcher
 * evaluation also live here so each event handler in index.ts becomes a
 * thin glue layer.
 */

import type { ExtensionContext } from "@earendil-works/pi-coding-agent";
import { spawn } from "node:child_process";
import { appendFileSync, mkdirSync, renameSync, statSync } from "node:fs";
import { dirname, join } from "node:path";

import type { SyntheticHookInvocationResult } from "../shared/hook-bridge.js";
import {
	blockingError,
	decodeGeneric,
	decodePermissionDenied,
	decodePermissionRequest,
	decodePreToolUse,
	plainTextContext,
	type PreToolPermission,
} from "./cc-protocol.js";
import { agentDir, basename } from "./config.js";
import type { HookEntryRuntime, HookEventName, HookGroup, HookRunResult } from "./types.js";

// ---------------------------------------------------------------------------
// Progress protocol — hooks may emit `^^PROGRESS <0-100> <message>` lines on
// stderr to surface a status string while running. The marker is stripped
// from the stderr that reaches the dispatcher (and ultimately the LLM
// feedback loop) so the protocol stays invisible to consumers that don't
// opt in.
// ---------------------------------------------------------------------------

const PROGRESS_LINE_RE = /^\^\^PROGRESS\s+(\d{1,3})\s+(.*)$/;

/**
 * Strip `^^PROGRESS N msg` markers from stderr so they never reach the LLM
 * feedback loop. The percent/message payload is discarded: nothing inside Pi
 * subscribes to it, and noisy hook stderr is worse than a missing status
 * update.
 */
export function extractProgress(stderr: string): { stderr: string } {
	if (!stderr.includes("^^PROGRESS")) return { stderr };
	const keep: string[] = [];
	for (const line of stderr.split(/\r?\n/)) {
		if (!PROGRESS_LINE_RE.test(line)) keep.push(line);
	}
	return { stderr: keep.join("\n") };
}

// ---------------------------------------------------------------------------
// Telemetry — JSONL append to ~/.pi/agent/logs/hooks.log. Best-effort: errors
// here must never propagate into dispatch.
// ---------------------------------------------------------------------------

const STDERR_HEAD_LIMIT = 500;
const TELEMETRY_MAX_BYTES = 10 * 1024 * 1024;

function telemetryLogPath(): string {
	// Computed on each call so test harnesses (and Pi sessions) that mutate
	// PI_CODING_AGENT_DIR see the change immediately. join() is cheap.
	return join(agentDir(), "logs", "hooks.log");
}

function rotateTelemetryIfTooLarge(path: string): void {
	try {
		const stats = statSync(path);
		if (stats.size > TELEMETRY_MAX_BYTES) {
			renameSync(path, path + ".1");
		}
	} catch {
		// File missing or unreadable — nothing to rotate.
	}
}

/** Build the JSONL line that `logHookTelemetry` would append. Pure function so
 * tests don't need a writable fs (the test harness module-mocks `node:fs`). */
export function buildTelemetryLine(entry: HookEntryRuntime, result: HookRunResult, durationMs: number, now: () => Date = () => new Date()): string {
	return JSON.stringify({
		ts: now().toISOString(),
		hook: basename(entry.config.command),
		event: entry.eventName,
		source: entry.source,
		exit_code: result.exitCode,
		duration_ms: durationMs,
		timed_out: result.timedOut,
		stderr_head: result.stderr.slice(0, STDERR_HEAD_LIMIT),
	});
}

/** Append one JSONL line describing the hook run. Swallows all errors. */
export function logHookTelemetry(entry: HookEntryRuntime, result: HookRunResult, durationMs: number): void {
	try {
		if (process.env.PI_HOOKS_DISABLE_TELEMETRY === "1") return;
		const line = buildTelemetryLine(entry, result, durationMs);
		const path = telemetryLogPath();
		mkdirSync(dirname(path), { recursive: true });
		rotateTelemetryIfTooLarge(path);
		appendFileSync(path, line + "\n");
	} catch {
		// Telemetry must never break dispatch.
	}
}

// ---------------------------------------------------------------------------
// Matcher evaluation
// ---------------------------------------------------------------------------

export function matcherMatches(matcher: string | undefined, ccToolName: string): boolean {
	if (!matcher || matcher === "" || matcher === "*") return true;
	try {
		return new RegExp(matcher, "i").test(ccToolName);
	} catch {
		return matcher.toLowerCase() === ccToolName.toLowerCase();
	}
}

export function matchingGroups(groups: HookGroup[], ccToolName: string): HookGroup[] {
	return groups.filter((g) => matcherMatches(g.matcher, ccToolName));
}

// ---------------------------------------------------------------------------
// Subprocess execution
// ---------------------------------------------------------------------------

export interface RunHookOptions {
	defaultTimeoutSec?: number;
	signal?: AbortSignal;
}

export const HOOK_OUTPUT_MAX_BYTES = 10 * 1024 * 1024;
const FALLBACK_PATH = "/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin";
const KILL_GRACE_MS = 1500;

function hookChildEnv(timeoutSec: number): NodeJS.ProcessEnv {
	const env = { ...process.env };
	// Guarantee a usable PATH — Pi may launch the runner with an empty or stripped
	// PATH, in which case `bash` itself can't be located. Mirrors the fallback
	// used inside individual hook scripts.
	if (!env.PATH || env.PATH.trim() === "") {
		env.PATH = FALLBACK_PATH;
	}
	// Hooks can self-bound before the runner terminates their process group.
	env.PI_HOOK_TIMEOUT_SEC = String(timeoutSec);
	return env;
}

const activeHooks = new Map<() => void, Promise<HookRunResult>>();

/** Cancel running session hooks and wait for process-group cleanup. */
export async function cancelRunningHooks(): Promise<void> {
	const pending = [...activeHooks.entries()];
	for (const [cancel] of pending) cancel();
	await Promise.all(pending.map(([, result]) => result));
}

export function runHook(entry: HookEntryRuntime, stdinJson: string, optionsOrDefault?: RunHookOptions | number): Promise<HookRunResult> {
	const options: RunHookOptions = typeof optionsOrDefault === "number" ? { defaultTimeoutSec: optionsOrDefault } : (optionsOrDefault ?? {});
	const timeoutSec = entry.config.timeout ?? options.defaultTimeoutSec ?? 30;
	if (process.platform === "win32") return Promise.resolve({ exitCode: 2, stdout: "", stderr: "Hook process-group cleanup requires a POSIX platform", timedOut: false });
	if (options.signal?.aborted) return Promise.resolve({ exitCode: 2, stdout: "", stderr: "Hook cancelled", timedOut: false });
	if (!Number.isFinite(timeoutSec) || timeoutSec <= 0) return Promise.resolve({ exitCode: 2, stdout: "", stderr: "Invalid hook timeout", timedOut: false });
	const started = Date.now();
	let cancel = () => {};
	const pending = new Promise<HookRunResult>((resolve) => {
		let settled = false;
		let stopReason: "timeout" | "cancelled" | "overflow" | undefined;
		let stdout = Buffer.alloc(0);
		let stderr = Buffer.alloc(0);
		let killTimer: ReturnType<typeof setTimeout> | undefined;
		const child = spawn("bash", ["-c", entry.config.command], {
			detached: true,
			env: hookChildEnv(timeoutSec),
			stdio: ["pipe", "pipe", "pipe"],
		});
		const signalTree = (signal: NodeJS.Signals) => {
			if (!child.pid) return;
			try {
				process.kill(-child.pid, signal);
			} catch (error) {
				if ((error as NodeJS.ErrnoException).code !== "ESRCH") child.kill(signal);
			}
		};
		const finish = (exitCode: number, errorText = "") => {
			if (settled) return;
			settled = true;
			clearTimeout(deadline);
			clearTimeout(killTimer);
			options.signal?.removeEventListener("abort", cancel);
			const cleaned = extractProgress(stderr.toString("utf8")).stderr;
			const notice = stopReason === "timeout" ? "Hook timed out" : stopReason === "cancelled" ? "Hook cancelled" : stopReason === "overflow" ? `Hook output exceeded ${HOOK_OUTPUT_MAX_BYTES / (1024 * 1024)}MB cap` : errorText;
			const result = { exitCode, stdout: stdout.toString("utf8"), stderr: [notice, cleaned].filter(Boolean).join(": "), timedOut: stopReason === "timeout" };
			logHookTelemetry(entry, result, Date.now() - started);
			resolve(result);
		};
		const stop = (reason: typeof stopReason) => {
			if (settled || stopReason) return;
			stopReason = reason;
			signalTree("SIGTERM");
			// Keep the group deadline even when bash exits first: descendants may
			// ignore TERM or close their stdio while continuing to run.
			killTimer = setTimeout(() => {
				signalTree("SIGKILL");
				child.stdin.destroy();
				child.stdout.destroy();
				child.stderr.destroy();
				finish(reason === "timeout" ? 1 : 2);
			}, KILL_GRACE_MS);
		};
		cancel = () => stop("cancelled");
		const deadline = setTimeout(() => stop("timeout"), timeoutSec * 1000);
		options.signal?.addEventListener("abort", cancel, { once: true });
		const collect = (chunk: Buffer, stream: "stdout" | "stderr") => {
			if (stopReason || settled) return;
			const current = stream === "stdout" ? stdout : stderr;
			const remaining = Math.max(0, HOOK_OUTPUT_MAX_BYTES - stdout.length - stderr.length);
			const next = Buffer.concat([current, chunk.subarray(0, remaining)]);
			if (stream === "stdout") stdout = next;
			else stderr = next;
			if (chunk.length > remaining) stop("overflow");
		};
		child.stdout.on("data", (chunk: Buffer) => collect(chunk, "stdout"));
		child.stderr.on("data", (chunk: Buffer) => collect(chunk, "stderr"));
		child.on("error", (error) => finish(2, error.message));
		child.on("close", (code) => {
			if (!stopReason) finish(code ?? 1);
		});
		child.stdin.on("error", () => {});
		child.stdin.end(stdinJson);
	});
	activeHooks.set(cancel, pending);
	void pending.finally(() => activeHooks.delete(cancel));
	return pending;
}

export function runHookAsync(
	entry: HookEntryRuntime,
	stdinJson: string,
	notifyFn: (msg: string, level: "error" | "warning") => void,
	defaultTimeoutSec = 60,
): void {
	runHook(entry, stdinJson, defaultTimeoutSec)
		.then((result) => {
			if (result.exitCode === 2 && result.stderr.trim()) {
				notifyFn(result.stderr.trim(), "warning");
			} else if (result.exitCode !== 0) {
				notifyFn(`Hook error (${commandLabel(entry)}): ${result.stderr || "non-zero exit"}`, "error");
			}
		})
		.catch(() => {
			// Stale extension context after session end — ignore silently
		});
}

function commandLabel(entry: HookEntryRuntime): string {
	return entry.config.command.split("/").at(-1) ?? entry.config.command;
}

// ---------------------------------------------------------------------------
// PreToolUse dispatch — decision rank: deny > defer > ask > allow
// ---------------------------------------------------------------------------

const PERMISSION_RANK: Record<PreToolPermission, number> = {
	allow: 1,
	ask: 2,
	defer: 3,
	deny: 4,
};

export async function runPreToolUseGroups(
	groups: HookGroup[],
	ccToolName: string,
	stdin: string,
	ctx?: ExtensionContext,
	defaultTimeout = 10,
): Promise<SyntheticHookInvocationResult> {
	let selectedPermission: PreToolPermission | undefined;
	let selectedReason = "";
	let selectedRank = 0;
	let updatedInput: Record<string, unknown> | undefined;
	const extraContexts: string[] = [];

	for (const group of matchingGroups(groups, ccToolName)) {
		for (const entry of group.hooks) {
			const result = await runHook(entry, stdin, defaultTimeout);
			if (result.timedOut) {
				return {
					blocked: true,
					reason: result.stderr.trim() || `Hook timed out: ${commandLabel(entry)}`,
					decision: "deny",
				};
			}
			const blocked = blockingError(result);
			if (blocked !== undefined) {
				return { blocked: true, reason: blocked, decision: "deny" };
			}
			if (result.exitCode !== 0) {
				ctx?.ui.notify(`Pre-tool hook error (${commandLabel(entry)}): ${result.stderr}`, "error");
				continue;
			}
			const decoded = decodePreToolUse(result.stdout);
			if (decoded.updatedInput) updatedInput = decoded.updatedInput;
			if (decoded.additionalContext) extraContexts.push(decoded.additionalContext);
			if (decoded.permission) {
				const rank = PERMISSION_RANK[decoded.permission];
				if (rank > selectedRank) {
					selectedRank = rank;
					selectedPermission = decoded.permission;
					selectedReason = decoded.reason ?? selectedReason;
				}
			}
		}
	}

	const additionalContext = extraContexts.join("\n").trim() || undefined;

	if (selectedPermission === "deny") {
		return { blocked: true, reason: selectedReason || "Blocked by hook", decision: "deny", updatedInput, additionalContext };
	}
	if (selectedPermission === "ask") {
		return {
			blocked: true,
			reason: selectedReason || "Blocked by hook: confirmation required (decision=ask)",
			decision: "ask",
			updatedInput,
			additionalContext,
		};
	}
	if (selectedPermission === "defer") {
		return {
			blocked: true,
			reason: selectedReason || "Deferred by hook (unsupported in interactive Pi)",
			decision: "defer",
			updatedInput,
			additionalContext,
		};
	}
	return { blocked: false, reason: selectedReason || undefined, decision: selectedPermission, updatedInput, additionalContext };
}

// ---------------------------------------------------------------------------
// PermissionRequest / PermissionDenied dispatch
// ---------------------------------------------------------------------------

export async function runPermissionRequestGroups(
	groups: HookGroup[],
	ccToolName: string,
	stdin: string,
	ctx?: ExtensionContext,
	defaultTimeout = 10,
): Promise<SyntheticHookInvocationResult> {
	for (const group of matchingGroups(groups, ccToolName)) {
		for (const entry of group.hooks) {
			const result = await runHook(entry, stdin, defaultTimeout);
			const blocked = blockingError(result);
			if (blocked !== undefined) {
				return { blocked: true, reason: blocked, behavior: "deny" };
			}
			if (result.exitCode !== 0) {
				ctx?.ui.notify(`PermissionRequest hook error (${commandLabel(entry)}): ${result.stderr}`, "error");
				continue;
			}
			const decoded = decodePermissionRequest(result.stdout);
			if (decoded.behavior === "deny") {
				return {
					blocked: true,
					reason: decoded.message || "Permission denied by hook",
					behavior: "deny",
					interrupt: decoded.interrupt,
				};
			}
			if (decoded.behavior === "allow") {
				return { blocked: false, behavior: "allow", updatedInput: decoded.updatedInput };
			}
		}
	}
	return { blocked: false };
}

export async function runPermissionDeniedGroups(
	groups: HookGroup[],
	ccToolName: string,
	stdin: string,
	ctx?: ExtensionContext,
): Promise<SyntheticHookInvocationResult> {
	let retry = false;
	for (const group of matchingGroups(groups, ccToolName)) {
		for (const entry of group.hooks) {
			const result = await runHook(entry, stdin, 10);
			if (result.exitCode !== 0) {
				ctx?.ui.notify(`PermissionDenied hook error (${commandLabel(entry)}): ${result.stderr}`, "error");
				continue;
			}
			const decoded = decodePermissionDenied(result.stdout);
			if (decoded.retry) retry = true;
		}
	}
	return { retry };
}

// ---------------------------------------------------------------------------
// Generic decision dispatch
// ---------------------------------------------------------------------------

// Events where a hook's `blocked: true` would have no addressable action to
// stop (post-fact notifications, idle signals, reload triggers). The bridge
// path collapses `blocked` to `false` for these so a misbehaving hook can't
// surface stale "denied" results to callers. UserPromptExpansion is *not*
// here because its local handler returns `{ action: "handled" }` and blocking
// is part of the contract.
export const NON_BLOCKING_HOOK_EVENTS = new Set<HookEventName>([
	"SessionStart",
	"Setup",
	"SessionEnd",
	"SubagentStart",
	"Notification",
	"PostCompact",
	"StopFailure",
	"InstructionsLoaded",
	"CwdChanged",
	"FileChanged",
	"WorktreeCreate",
	"WorktreeRemove",
	"PostToolBatch",
	"TaskCreated",
	"TaskCompleted",
	"TeammateIdle",
	"ConfigChange",
	"Elicitation",
	"ElicitationResult",
]);

export async function runDecisionHooks(
	hookName: HookEventName,
	groups: HookGroup[],
	stdin: string,
	ctx?: ExtensionContext,
): Promise<{ blocked: boolean; reason?: string; additionalContext?: string }> {
	let blocked = false;
	let blockReason = "";
	const contexts: string[] = [];
	for (const group of groups) {
		for (const entry of group.hooks) {
			const result = await runHook(entry, stdin, 15);
			const blockingMsg = blockingError(result);
			if (blockingMsg !== undefined) {
				// Record the block but keep iterating: callers of runDecisionHooks
				// (UserPromptSubmit, UserPromptExpansion, CwdChanged, PostToolBatch,
				// bridge events) accumulate `additionalContext` from every entry. The
				// PreToolUse / PermissionRequest dispatchers short-circuit instead,
				// because their decisions are mutually exclusive.
				blocked = true;
				blockReason = blockingMsg;
				continue;
			}
			if (result.exitCode !== 0) {
				ctx?.ui.notify(`${hookName} hook error (${commandLabel(entry)}): ${result.stderr}`, "error");
				continue;
			}
			const decoded = decodeGeneric(result.stdout, hookName);
			if (decoded.block) {
				blocked = true;
				blockReason = decoded.reason || blockReason || `${hookName} blocked by hook`;
			}
			if (decoded.additionalContext) {
				contexts.push(decoded.additionalContext);
			} else {
				const plain = plainTextContext(result);
				if (plain) contexts.push(plain);
			}
		}
	}
	return {
		blocked,
		reason: blockReason || undefined,
		additionalContext: contexts.join("\n").trim() || undefined,
	};
}

// ---------------------------------------------------------------------------
// Utilities shared with the event-handler layer
// ---------------------------------------------------------------------------

export function replaceInput(target: Record<string, unknown>, replacement: Record<string, unknown>): void {
	for (const key of Object.keys(target)) {
		delete target[key];
	}
	Object.assign(target, replacement);
}

export function serializeToolContent(content: Array<{ type: string; text?: string }>): string {
	const parts: string[] = [];
	for (const block of content) {
		if (block.type === "text" && typeof block.text === "string") {
			parts.push(block.text);
			continue;
		}
		if (block.type === "image") {
			parts.push("[image]");
		}
	}
	return parts.join("\n");
}

export function parseSlashCommand(text: string): { commandName: string; commandArgs: string; prompt: string } | undefined {
	const trimmed = text.trim();
	if (!trimmed.startsWith("/") || trimmed.startsWith("//")) return undefined;
	const withoutSlash = trimmed.slice(1).trim();
	if (!withoutSlash) return undefined;
	const [commandName, ...rest] = withoutSlash.split(/\s+/);
	if (!commandName) return undefined;
	return {
		commandName,
		commandArgs: rest.join(" "),
		prompt: trimmed,
	};
}
