/**
 * Claude Code hook wire-protocol anti-corruption layer.
 *
 * Anthropic owns the spec; cc-thingz shadows it by imitation. Every field
 * name and exit-code convention that mirrors CC's hook protocol lives here
 * and nowhere else. Callers see four event-specific decision shapes
 * (PreToolUseDecision, PermissionRequestDecision, PermissionDeniedDecision,
 * GenericDecision) that are owned by cc-thingz, not by Anthropic.
 *
 * When CC adds a field or changes a wire name, the edit lives in this file.
 * Dispatchers consume the decoded decisions and apply aggregation rules
 * without re-parsing.
 */

import type { HookEventName, HookRunResult } from "./types.js";
import { isRecord } from "./types.js";

// ---------------------------------------------------------------------------
// Decoded decision shapes — owned by cc-thingz
// ---------------------------------------------------------------------------

export type PreToolPermission = "allow" | "ask" | "deny" | "defer";

export interface PreToolUseDecision {
	permission?: PreToolPermission;
	reason?: string;
	updatedInput?: Record<string, unknown>;
	additionalContext?: string;
}

export interface PermissionRequestDecision {
	behavior?: "allow" | "deny";
	message?: string;
	interrupt?: boolean;
	updatedInput?: Record<string, unknown>;
}

export interface PermissionDeniedDecision {
	retry?: boolean;
}

export interface GenericDecision {
	block: boolean;
	reason?: string;
	additionalContext?: string;
}

// ---------------------------------------------------------------------------
// Wire-format helpers — only this module reads CC field names
// ---------------------------------------------------------------------------

function parseJsonObject(raw: string): Record<string, unknown> | undefined {
	const trimmed = raw.trim();
	if (!trimmed) return undefined;
	try {
		const parsed = JSON.parse(trimmed) as unknown;
		if (!isRecord(parsed)) return undefined;
		return parsed;
	} catch {
		return undefined;
	}
}

/**
 * CC-style `hookSpecificOutput` envelope check. Returns the wrapped object
 * only when the hook declared the correct event name (or omitted the field).
 */
function hookSpecificOutput(parsed: Record<string, unknown>, hookEventName: HookEventName): Record<string, unknown> | undefined {
	const raw = parsed.hookSpecificOutput;
	if (!isRecord(raw)) return undefined;
	const declared = raw.hookEventName;
	if (typeof declared === "string" && declared !== hookEventName) {
		return undefined;
	}
	return raw;
}

function stringField(...candidates: unknown[]): string | undefined {
	for (const candidate of candidates) {
		if (typeof candidate === "string") return candidate;
	}
	return undefined;
}

function recordField(value: unknown): Record<string, unknown> | undefined {
	return isRecord(value) ? value : undefined;
}

// ---------------------------------------------------------------------------
// Decoders
// ---------------------------------------------------------------------------

function normalisePermission(value: string | undefined): PreToolPermission | undefined {
	if (value === "approve") return "allow";
	if (value === "block") return "deny";
	if (value === "allow" || value === "ask" || value === "deny" || value === "defer") {
		return value;
	}
	return undefined;
}

export function decodePreToolUse(stdout: string): PreToolUseDecision {
	const parsed = parseJsonObject(stdout);
	if (!parsed) return {};
	const hso = hookSpecificOutput(parsed, "PreToolUse") ?? parsed;

	const rawPermission = stringField(hso.permissionDecision) ?? stringField(hso.decision) ?? stringField(parsed.decision);
	const permission = normalisePermission(rawPermission);

	const reason = stringField(hso.permissionDecisionReason) ?? stringField(hso.reason) ?? stringField(parsed.reason);

	const additionalContext = stringField(hso.additionalContext) ?? stringField(parsed.additionalContext);
	const updatedInput = recordField(hso.updatedInput);

	return { permission, reason, updatedInput, additionalContext };
}

export function decodePermissionRequest(stdout: string): PermissionRequestDecision {
	const parsed = parseJsonObject(stdout);
	if (!parsed) return {};
	const hso = hookSpecificOutput(parsed, "PermissionRequest");
	if (!hso) return {};
	const decision = recordField(hso.decision);
	if (!decision) return {};
	const behavior = decision.behavior;
	if (behavior !== "allow" && behavior !== "deny") return {};
	return {
		behavior,
		message: stringField(decision.message),
		interrupt: typeof decision.interrupt === "boolean" ? decision.interrupt : undefined,
		updatedInput: recordField(decision.updatedInput),
	};
}

export function decodePermissionDenied(stdout: string): PermissionDeniedDecision {
	const parsed = parseJsonObject(stdout);
	if (!parsed) return {};
	const hso = hookSpecificOutput(parsed, "PermissionDenied");
	if (!hso) return {};
	return { retry: hso.retry === true };
}

export function decodeGeneric(stdout: string, hookEventName: HookEventName): GenericDecision {
	const parsed = parseJsonObject(stdout);
	if (!parsed) return { block: false };
	const hso = hookSpecificOutput(parsed, hookEventName) ?? parsed;
	const decision = stringField(hso.decision) ?? stringField(parsed.decision);
	const continueField = typeof hso.continue === "boolean" ? hso.continue : typeof parsed.continue === "boolean" ? parsed.continue : undefined;
	const reason = stringField(hso.reason) ?? stringField(parsed.reason) ?? stringField(hso.stopReason) ?? stringField(parsed.stopReason);
	const additionalContext = stringField(hso.additionalContext) ?? stringField(parsed.additionalContext);
	// Precedence: either signal blocks. A hook that emits `decision: "block"`
	// alongside `continue: true` is still blocked — explicit `decision` always
	// wins. CC's spec treats both as blocking signals, OR'd together.
	return {
		block: decision === "block" || continueField === false,
		reason,
		additionalContext,
	};
}

// ---------------------------------------------------------------------------
// Exit-code conventions — CC's exit-code-2-blocks rule lives here
// ---------------------------------------------------------------------------

/**
 * CC convention: exit code 2 means "block, stderr is the reason".
 * Returns the reason string when the result is a blocking signal, otherwise
 * undefined. Dispatchers use this to short-circuit without re-implementing
 * the rule.
 */
export function blockingError(result: HookRunResult): string | undefined {
	if (result.exitCode !== 2) return undefined;
	const reason = result.stderr.trim();
	return reason || "Blocked by hook";
}

/**
 * When a generic-decision hook emits non-JSON stdout, the convention is to
 * treat the stdout as additional context. This separates "stdout is a hook
 * decision" from "stdout is free-form extra context".
 */
export function plainTextContext(result: HookRunResult): string | undefined {
	const trimmed = result.stdout.trim();
	if (!trimmed) return undefined;
	if (parseJsonObject(trimmed)) return undefined;
	return trimmed;
}
