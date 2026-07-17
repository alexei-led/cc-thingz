import type { ExtensionAPI, ExtensionContext } from "@earendil-works/pi-coding-agent";

/** Event-bus channel used by extensions to invoke hook-runner synthetic hook dispatch. */
export const HOOK_RUNNER_INVOKE_CHANNEL = "cc-hooks:invoke";

/**
 * Pi tool name (lowercase, snake_case) → CC tool name (PascalCase or domain-specific).
 *
 * Lives here so every consumer that needs a CC name uses the same mapping —
 * hook-runner's dispatcher, permission-gate's PermissionRequest stdin builder,
 * and plan-mode's ExitPlanMode synthetic invocation all share this table.
 */
const TOOL_NAME_MAP: Record<string, string> = {
	bash: "Bash",
	write: "Write",
	edit: "Edit",
	multiedit: "MultiEdit",
	read: "Read",
	grep: "Grep",
	find: "Glob",
	ls: "Ls",
	subagent: "Agent",
	ask_user_question: "AskUserQuestion",
	exit_plan_mode: "ExitPlanMode",
};

/**
 * Resolve a Pi tool name to its CC equivalent.
 *
 * Unregistered lowercase names fall back to capitalize-first-letter to match
 * legacy behaviour (`finder` → `Finder`). Anything containing underscores or
 * already-mixed case is returned as-is — explicit registration is required
 * for those, so callers get a stable name rather than silent inference.
 */
export function toCcToolName(piName: string): string {
	const mapped = TOOL_NAME_MAP[piName.toLowerCase()];
	if (mapped !== undefined) return mapped;
	if (piName === piName.toLowerCase() && !piName.includes("_")) {
		return piName.charAt(0).toUpperCase() + piName.slice(1);
	}
	return piName;
}

/** Synthetic hook event names accepted by hook-runner bridge invocations. */
export const SYNTHETIC_HOOK_EVENT_NAMES = [
	"PreToolUse",
	"PermissionRequest",
	"PermissionDenied",
	"TaskCreated",
	"TaskCompleted",
	"PostToolBatch",
	"UserPromptExpansion",
	"Setup",
	"StopFailure",
	"TeammateIdle",
	"InstructionsLoaded",
	"ConfigChange",
	"CwdChanged",
	"FileChanged",
	"WorktreeCreate",
	"WorktreeRemove",
	"Elicitation",
	"ElicitationResult",
] as const;

export type SyntheticHookEventName = (typeof SYNTHETIC_HOOK_EVENT_NAMES)[number];

type SyntheticHookBaseResult = {
	blocked?: boolean;
	reason?: string;
	updatedInput?: Record<string, unknown>;
	additionalContext?: string;
	worktreePath?: string;
};

type SyntheticPreToolUseResult = SyntheticHookBaseResult & {
	decision?: "allow" | "ask" | "deny" | "defer";
	behavior?: never;
	retry?: never;
	message?: never;
	interrupt?: never;
};

type SyntheticPermissionRequestResult = SyntheticHookBaseResult & {
	behavior?: "allow" | "deny";
	message?: string;
	interrupt?: boolean;
	decision?: never;
	retry?: never;
};

type SyntheticPermissionDeniedResult = SyntheticHookBaseResult & {
	retry?: boolean;
	decision?: never;
	behavior?: never;
	message?: never;
	interrupt?: never;
};

type SyntheticGenericResult = SyntheticHookBaseResult & {
	decision?: never;
	behavior?: never;
	retry?: never;
	message?: never;
	interrupt?: never;
};

export type SyntheticHookInvocationResult =
	| SyntheticPreToolUseResult
	| SyntheticPermissionRequestResult
	| SyntheticPermissionDeniedResult
	| SyntheticGenericResult;

/**
 * Wire shape published on `HOOK_RUNNER_INVOKE_CHANNEL`.
 *
 * Callers do not construct this directly — they use `invokeSyntheticHook`,
 * which has its own request type and supplies `onResult` internally. The
 * field lives on this interface because it travels over the event bus to
 * the hook-runner side, which must call it to deliver the result.
 */
export interface SyntheticHookInvocationRequest {
	hookEventName: SyntheticHookEventName;
	stdin: Record<string, unknown>;
	ccToolName?: string;
	timeoutSec?: number;
	/** Set by `invokeSyntheticHook`; consumed by the hook-runner bridge. Not for extension callers. */
	onResult?: (result: SyntheticHookInvocationResult) => void;
}

/**
 * Margin added on top of the per-subprocess timeout when deriving the outer
 * wait — gives hook-runner room to schedule the callback after its own timer
 * fires.
 */
export const SYNTHETIC_HOOK_OUTER_WAIT_MARGIN_MS = 30_000;

/** Default per-subprocess timeout when neither caller nor hook entry sets one. */
export const SYNTHETIC_HOOK_DEFAULT_TIMEOUT_SEC = 10;

/**
 * Shared synthetic-hook caller for extensions.
 *
 * Two timeouts apply:
 * - `timeoutSec` bounds the hook subprocess inside hook-runner. Forwarded to
 *   hook-runner; individual hook entries with their own `timeout` field
 *   override this per-entry. Default 10s.
 * - `timeoutMs` is the outer wait on this side for hook-runner to call back.
 *   When omitted it is computed as `timeoutSec * 1000 + SYNTHETIC_HOOK_OUTER_WAIT_MARGIN_MS`
 *   so the per-entry timer reliably fires first. Explicit caller-supplied
 *   values are honored verbatim — short outer waits are valid for interactive
 *   flows (e.g. permission-gate's 2s deadline) where waiting on a missing
 *   hook-runner response would block the user.
 *
 * Trade-off: a short explicit `timeoutMs` causes the outer wait to fire before
 * hook-runner's per-entry timer — the caller's `timeoutResult` is returned
 * regardless of what the hook would have decided. Interactive callers want
 * this (snappy fail-closed). Non-interactive callers should set
 * `enforceFloor: true` to clamp `timeoutMs` up to the floor and prevent the
 * outer wait from preempting the per-entry deadline.
 *
 * Returns `timeoutResult` when hook-runner does not respond before `timeoutMs`.
 * Returns `{}` when context/session/event bus is unavailable.
 */
export async function invokeSyntheticHook(
	pi: ExtensionAPI,
	ctx: ExtensionContext,
	request: {
		hookEventName: SyntheticHookEventName;
		stdin: Record<string, unknown>;
		ccToolName?: string;
		timeoutSec?: number;
		timeoutMs?: number;
		/** Clamp explicit `timeoutMs` up to `timeoutSec*1000 + margin` for non-interactive flows. */
		enforceFloor?: boolean;
		timeoutResult?: SyntheticHookInvocationResult;
	},
): Promise<SyntheticHookInvocationResult> {
	if (!ctx || typeof ctx !== "object") return {};
	if (typeof ctx.sessionManager?.getSessionId?.() !== "string") return {};
	if (typeof ctx.cwd !== "string") return {};
	if (!pi.events || typeof pi.events.emit !== "function") return {};

	const timeoutSec = request.timeoutSec ?? SYNTHETIC_HOOK_DEFAULT_TIMEOUT_SEC;
	const floor = timeoutSec * 1000 + SYNTHETIC_HOOK_OUTER_WAIT_MARGIN_MS;
	let timeoutMs = request.timeoutMs ?? floor;
	if (request.enforceFloor && timeoutMs < floor) {
		timeoutMs = floor;
	}

	return await new Promise((resolve) => {
		let settled = false;
		const done = (value: SyntheticHookInvocationResult) => {
			if (settled) return;
			settled = true;
			resolve(value);
		};
		const timer = setTimeout(() => done(request.timeoutResult ?? {}), timeoutMs);
		try {
			pi.events.emit(HOOK_RUNNER_INVOKE_CHANNEL, {
				hookEventName: request.hookEventName,
				ccToolName: request.ccToolName,
				stdin: request.stdin,
				timeoutSec,
				onResult: (result: SyntheticHookInvocationResult) => {
					clearTimeout(timer);
					done(result);
				},
			});
		} catch {
			// Event bus torn down (e.g., session ended mid-call). Fail-closed for
			// non-interactive callers requires the caller to set timeoutResult;
			// without one, return an empty result so callers treat it as "no
			// decision" rather than waiting out the full outer timeout.
			clearTimeout(timer);
			done({});
		}
	});
}
