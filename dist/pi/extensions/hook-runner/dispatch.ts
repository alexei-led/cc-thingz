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
import { execFile } from "node:child_process";
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
}

export const HOOK_OUTPUT_MAX_BYTES = 10 * 1024 * 1024;
const FALLBACK_PATH = "/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin";
// execFile's own `timeout` sends SIGTERM at the deadline, not SIGKILL. A child
// that traps SIGTERM never exits and execFile's callback never fires. This is
// how long runHook waits after that SIGTERM before force-killing directly.
const KILL_GRACE_MS = 1500;

/**
 * Translate an execFile callback (`error`, `stdout`, `stderr`) into the canonical
 * `HookRunResult`. Extracted from `runHook` so the timeout/overflow/error-code
 * branches are testable as a pure function — bun's process-wide module mock on
 * `node:child_process` makes real-subprocess assertions impossible inside the
 * shared test suite.
 */
export function classifyExecResult(error: unknown, stdout: string, cleanedStderr: string): HookRunResult {
	if (!error) {
		return { exitCode: 0, stdout, stderr: cleanedStderr, timedOut: false };
	}
	const err = error as Error & { killed?: boolean; code?: unknown };
	const killed = err.killed ?? false;
	// Output overflow is reported via a string code, not a numeric exit.
	// Treat it as a blocking signal so the dispatcher returns a deny rather
	// than silently dropping the hook's would-be decision.
	const codeStr = typeof err.code === "string" ? err.code : "";
	const overflowed = codeStr === "ERR_CHILD_PROCESS_STDIO_MAXBUFFER";
	const exitCode = overflowed ? 2 : typeof err.code === "number" ? err.code : 1;
	// `maxBuffer` caps stdout+stderr combined, so a non-empty stderr at
	// overflow is unrelated noise — prepending the explicit cap notice keeps
	// the actionable signal first while preserving the captured stderr.
	const overflowStderr = `Hook output exceeded ${HOOK_OUTPUT_MAX_BYTES / (1024 * 1024)}MB cap`;
	const stderrOut = overflowed ? (cleanedStderr.trim() ? `${overflowStderr}: ${cleanedStderr}` : overflowStderr) : cleanedStderr;
	return { exitCode, stdout, stderr: stderrOut, timedOut: killed };
}

function hookChildEnv(timeoutSec: number): NodeJS.ProcessEnv {
	const env = { ...process.env };
	// Guarantee a usable PATH — Pi may launch the runner with an empty or stripped
	// PATH, in which case `bash` itself can't be located. Mirrors the fallback
	// used inside individual hook scripts.
	if (!env.PATH || env.PATH.trim() === "") {
		env.PATH = FALLBACK_PATH;
	}
	// Surface the effective timeout to the hook so it can self-bound and emit a
	// proper blocking exit (2) before the deadline: execFile sends SIGTERM at
	// `timeoutSec`, and runHook force-SIGKILLs at `timeoutSec + KILL_GRACE_MS`
	// if the child is still alive by then.
	env.PI_HOOK_TIMEOUT_SEC = String(timeoutSec);
	return env;
}

export function runHook(entry: HookEntryRuntime, stdinJson: string, optionsOrDefault?: RunHookOptions | number): Promise<HookRunResult> {
	const options: RunHookOptions = typeof optionsOrDefault === "number" ? { defaultTimeoutSec: optionsOrDefault } : (optionsOrDefault ?? {});
	const defaultTimeoutSec = options.defaultTimeoutSec ?? 30;
	const started = Date.now();
	return new Promise((resolve) => {
		const timeoutSec = entry.config.timeout ?? defaultTimeoutSec;
		const timeoutMs = timeoutSec * 1000;
		let settled = false;
		const child = execFile(
			"bash",
			["-c", entry.config.command],
			{ timeout: timeoutMs, env: hookChildEnv(timeoutSec), maxBuffer: HOOK_OUTPUT_MAX_BYTES },
			(error, stdout, stderr) => {
				if (settled) return;
				settled = true;
				clearTimeout(killTimer);
				const { stderr: cleanedStderr } = extractProgress(stderr ?? "");
				const result = classifyExecResult(error, stdout, cleanedStderr);
				logHookTelemetry(entry, result, Date.now() - started);
				resolve(result);
			},
		);
		// Fallback kill timer, independent of execFile's own `timeout`. execFile
		// sends SIGTERM at the deadline; a child that traps SIGTERM (or has a
		// descendant holding its stdio pipes open) never causes the callback
		// above to fire. This fires KILL_GRACE_MS later and force-kills directly.
		//
		// Accepted tradeoff: this only signals `child` itself — orphaned
		// descendants are not reaped. On Node 24 and Bun 1.3.14, execFile ignores
		// `detached: true` and a negative-pid `process.kill(-pid)` ESRCHes every
		// time, so a positive-pid SIGKILL via `child.kill` is the lever that
		// actually works. The descendant-held-pipe case is already force-resolved
		// by execFile's own timeout close to the deadline; this timer's job is
		// the SIGTERM-trapping-child case, where execFile's SIGTERM never causes
		// an exit and its callback never fires.
		const killTimer = setTimeout(() => {
			if (settled) return;
			try {
				child.kill("SIGKILL");
			} catch {
				// Process already gone — nothing to do.
			}
			settled = true;
			const result: HookRunResult = { exitCode: 1, stdout: "", stderr: "hook timed out (killed)", timedOut: true };
			logHookTelemetry(entry, result, Date.now() - started);
			resolve(result);
		}, timeoutMs + KILL_GRACE_MS);
		child.stdin?.write(stdinJson);
		child.stdin?.end();
	});
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
