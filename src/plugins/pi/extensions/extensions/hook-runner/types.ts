import { SYNTHETIC_HOOK_EVENT_NAMES } from "../shared/hook-bridge.js";

// `SubagentStart` / `SubagentStop` are included for CC schema compatibility
// (Claude Code emits them natively). Pi has no reliable subagent lifecycle
// runtime events yet, so hooks registered under these keys never fire — see
// docs/pi-extensions.md for the supported-events table.
export const CORE_HOOK_EVENT_NAMES = [
	"PostToolUse",
	"PostToolUseFailure",
	"SessionStart",
	"SessionEnd",
	"SubagentStart",
	"SubagentStop",
	"UserPromptSubmit",
	"Stop",
	"Notification",
	"PreCompact",
	"PostCompact",
] as const;

export const HOOK_EVENT_NAMES = [...SYNTHETIC_HOOK_EVENT_NAMES, ...CORE_HOOK_EVENT_NAMES] as const;

export type HookEventName = (typeof HOOK_EVENT_NAMES)[number];

export function isHookEventName(value: unknown): value is HookEventName {
	return typeof value === "string" && (HOOK_EVENT_NAMES as readonly string[]).includes(value);
}

/**
 * Where a loaded hook entry came from.
 * - `bundled`: ships with cc-thingz under dist/pi/extensions/hooks.json
 * - `global`: user-level `~/.pi/agent/{settings,hooks}.json`
 * - `project`: per-project `.pi/{settings,hooks}.json`
 * - `package`: contributed by an installed Pi package via `cc-thingz.hooks`
 *   in its `package.json` (auto-discovered at session start).
 */
export type HookSource = "bundled" | "global" | "project" | "package";

/** Wire shape parsed verbatim from hooks.json (bundled or user-supplied). */
export interface HookEntryConfig {
	type: "command";
	command: string;
	/** Seconds; default varies by event family. */
	timeout?: number;
	/** Fire-and-forget — runHookAsync does not block the dispatcher. */
	async?: boolean;
}

/** Loaded view of a hook entry: parsed config + runtime tagging. */
export interface HookEntryRuntime {
	config: HookEntryConfig;
	source: HookSource;
	disabled: boolean;
	/**
	 * Event key the entry was loaded under (e.g. `PreToolUse`, `Stop`). Kept
	 * for telemetry so JSONL lines carry the event name regardless of which
	 * dispatcher invoked the entry. Typed as `string` because `HooksConfig`
	 * accepts arbitrary keys via its index signature.
	 */
	eventName: string;
}

export interface HookGroup {
	/** Regex matched case-insensitively against the CC-style tool name. undefined = match all. */
	matcher?: string;
	hooks: HookEntryRuntime[];
}

export interface HooksConfig {
	PreToolUse?: HookGroup[];
	PostToolUse?: HookGroup[];
	PostToolUseFailure?: HookGroup[];
	PostToolBatch?: HookGroup[];
	SessionStart?: HookGroup[];
	Setup?: HookGroup[];
	SessionEnd?: HookGroup[];
	/** @deprecated Accepted for Claude Code schema compatibility; Pi has no native subagent-start event so registered hooks never fire. */
	SubagentStart?: HookGroup[];
	/** @deprecated Accepted for Claude Code schema compatibility; Pi has no native subagent-stop event so registered hooks never fire. */
	SubagentStop?: HookGroup[];
	UserPromptSubmit?: HookGroup[];
	UserPromptExpansion?: HookGroup[];
	Stop?: HookGroup[];
	StopFailure?: HookGroup[];
	TeammateIdle?: HookGroup[];
	InstructionsLoaded?: HookGroup[];
	ConfigChange?: HookGroup[];
	CwdChanged?: HookGroup[];
	FileChanged?: HookGroup[];
	PreCompact?: HookGroup[];
	PostCompact?: HookGroup[];
	Notification?: HookGroup[];
	PermissionRequest?: HookGroup[];
	PermissionDenied?: HookGroup[];
	TaskCreated?: HookGroup[];
	TaskCompleted?: HookGroup[];
	WorktreeCreate?: HookGroup[];
	WorktreeRemove?: HookGroup[];
	Elicitation?: HookGroup[];
	ElicitationResult?: HookGroup[];
	[key: string]: HookGroup[] | undefined;
}

export interface HookRunResult {
	exitCode: number;
	stdout: string;
	stderr: string;
	timedOut: boolean;
}

export interface HookRunnerOptions {
	disableBundledHooks?: boolean;
	/** Command basenames to skip. */
	disabledHooks?: string[];
}

export function isRecord(value: unknown): value is Record<string, unknown> {
	return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}
