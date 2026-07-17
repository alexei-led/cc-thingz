import { describe, expect, it } from "bun:test";

import { blockingError, decodeGeneric, decodePermissionDenied, decodePermissionRequest, decodePreToolUse, plainTextContext } from "../../../src/plugins/pi/extensions/extensions/hook-runner/cc-protocol.ts";

// ---------------------------------------------------------------------------
// decodePreToolUse
// ---------------------------------------------------------------------------

describe("decodePreToolUse", () => {
	it("returns empty object on empty stdout", () => {
		expect(decodePreToolUse("")).toEqual({});
		expect(decodePreToolUse("   ")).toEqual({});
	});

	it("returns empty object on non-JSON stdout", () => {
		expect(decodePreToolUse("not json")).toEqual({});
	});

	it("ignores JSON arrays at the top level", () => {
		expect(decodePreToolUse("[1,2,3]")).toEqual({});
	});

	it("reads permissionDecision from hookSpecificOutput envelope", () => {
		const stdout = JSON.stringify({
			hookSpecificOutput: { hookEventName: "PreToolUse", permissionDecision: "deny", permissionDecisionReason: "no" },
		});
		expect(decodePreToolUse(stdout)).toMatchObject({ permission: "deny", reason: "no" });
	});

	it.each([
		["approve", "allow"],
		["block", "deny"],
		["allow", "allow"],
		["ask", "ask"],
		["deny", "deny"],
		["defer", "defer"],
	] as const)("normalises legacy decision %p to %p", (input, expected) => {
		const stdout = JSON.stringify({ decision: input });
		expect(decodePreToolUse(stdout).permission).toBe(expected);
	});

	it("drops unknown decision values", () => {
		const stdout = JSON.stringify({ decision: "redirect" });
		expect(decodePreToolUse(stdout).permission).toBeUndefined();
	});

	it("falls back to top-level reason when hookSpecificOutput lacks one", () => {
		const stdout = JSON.stringify({ reason: "top-level" });
		expect(decodePreToolUse(stdout).reason).toBe("top-level");
	});

	it("captures updatedInput and additionalContext", () => {
		const stdout = JSON.stringify({
			hookSpecificOutput: {
				hookEventName: "PreToolUse",
				updatedInput: { command: "echo safe" },
				additionalContext: "extra",
			},
		});
		expect(decodePreToolUse(stdout)).toEqual({
			permission: undefined,
			reason: undefined,
			updatedInput: { command: "echo safe" },
			additionalContext: "extra",
		});
	});

	it("rejects hookSpecificOutput when hookEventName declared as a different event", () => {
		const stdout = JSON.stringify({
			hookSpecificOutput: { hookEventName: "PostToolUse", permissionDecision: "deny" },
		});
		// Mis-tagged envelope ignored; falls back to top-level — no decision present.
		expect(decodePreToolUse(stdout).permission).toBeUndefined();
	});
});

// ---------------------------------------------------------------------------
// decodePermissionRequest
// ---------------------------------------------------------------------------

describe("decodePermissionRequest", () => {
	it("returns empty object without hookSpecificOutput envelope", () => {
		expect(decodePermissionRequest(JSON.stringify({ decision: { behavior: "allow" } }))).toEqual({});
	});

	it("rejects decision shapes that are not objects", () => {
		const stdout = JSON.stringify({ hookSpecificOutput: { hookEventName: "PermissionRequest", decision: "allow" } });
		expect(decodePermissionRequest(stdout)).toEqual({});
	});

	it("rejects unknown behavior values", () => {
		const stdout = JSON.stringify({
			hookSpecificOutput: { hookEventName: "PermissionRequest", decision: { behavior: "maybe" } },
		});
		expect(decodePermissionRequest(stdout)).toEqual({});
	});

	it("returns full decision when allow", () => {
		const stdout = JSON.stringify({
			hookSpecificOutput: {
				hookEventName: "PermissionRequest",
				decision: { behavior: "allow", updatedInput: { command: "rm -rf /tmp" }, interrupt: false },
			},
		});
		expect(decodePermissionRequest(stdout)).toEqual({
			behavior: "allow",
			message: undefined,
			interrupt: false,
			updatedInput: { command: "rm -rf /tmp" },
		});
	});

	it("returns deny with message", () => {
		const stdout = JSON.stringify({
			hookSpecificOutput: {
				hookEventName: "PermissionRequest",
				decision: { behavior: "deny", message: "blocked by policy", interrupt: true },
			},
		});
		expect(decodePermissionRequest(stdout)).toEqual({
			behavior: "deny",
			message: "blocked by policy",
			interrupt: true,
			updatedInput: undefined,
		});
	});
});

// ---------------------------------------------------------------------------
// decodePermissionDenied
// ---------------------------------------------------------------------------

describe("decodePermissionDenied", () => {
	it("returns empty object when envelope missing", () => {
		expect(decodePermissionDenied(JSON.stringify({ retry: true }))).toEqual({});
	});

	it("returns retry true when set", () => {
		const stdout = JSON.stringify({ hookSpecificOutput: { hookEventName: "PermissionDenied", retry: true } });
		expect(decodePermissionDenied(stdout)).toEqual({ retry: true });
	});

	it("returns retry false when missing", () => {
		const stdout = JSON.stringify({ hookSpecificOutput: { hookEventName: "PermissionDenied" } });
		expect(decodePermissionDenied(stdout)).toEqual({ retry: false });
	});
});

// ---------------------------------------------------------------------------
// decodeGeneric
// ---------------------------------------------------------------------------

describe("decodeGeneric", () => {
	it("returns block:false on empty stdout", () => {
		expect(decodeGeneric("", "PostToolUse")).toEqual({ block: false });
	});

	it("blocks on decision=block", () => {
		expect(decodeGeneric(JSON.stringify({ decision: "block", reason: "lint failed" }), "PostToolUse")).toEqual({
			block: true,
			reason: "lint failed",
			additionalContext: undefined,
		});
	});

	it("blocks on continue:false", () => {
		expect(decodeGeneric(JSON.stringify({ continue: false }), "Stop")).toMatchObject({ block: true });
	});

	it("prefers top-level reason over hookSpecificOutput.stopReason (cascade order)", () => {
		const stdout = JSON.stringify({
			hookSpecificOutput: { hookEventName: "Stop", decision: "block", stopReason: "inner" },
			reason: "outer",
		});
		// Cascade is hso.reason ?? parsed.reason ?? hso.stopReason ?? parsed.stopReason.
		// No hso.reason here, so top-level `reason` wins over `stopReason`.
		expect(decodeGeneric(stdout, "Stop")).toMatchObject({ block: true, reason: "outer" });
	});

	it("captures additionalContext", () => {
		const stdout = JSON.stringify({ additionalContext: "more info" });
		expect(decodeGeneric(stdout, "UserPromptSubmit")).toEqual({
			block: false,
			reason: undefined,
			additionalContext: "more info",
		});
	});
});

// ---------------------------------------------------------------------------
// blockingError / plainTextContext
// ---------------------------------------------------------------------------

describe("blockingError", () => {
	it("returns stderr trimmed when exit code 2", () => {
		expect(blockingError({ exitCode: 2, stdout: "", stderr: "  bad input  ", timedOut: false })).toBe("bad input");
	});

	it("returns default message when exit 2 with empty stderr", () => {
		expect(blockingError({ exitCode: 2, stdout: "", stderr: "", timedOut: false })).toBe("Blocked by hook");
	});

	it("returns undefined for other exit codes", () => {
		expect(blockingError({ exitCode: 0, stdout: "", stderr: "", timedOut: false })).toBeUndefined();
		expect(blockingError({ exitCode: 1, stdout: "", stderr: "error", timedOut: false })).toBeUndefined();
	});
});

describe("plainTextContext", () => {
	it("returns trimmed stdout when not JSON", () => {
		expect(plainTextContext({ exitCode: 0, stdout: "  hello world  \n", stderr: "", timedOut: false })).toBe("hello world");
	});

	it("returns undefined when stdout parses as JSON object", () => {
		expect(plainTextContext({ exitCode: 0, stdout: '{"key":"value"}', stderr: "", timedOut: false })).toBeUndefined();
	});

	it("returns the text when stdout is JSON-looking but not an object", () => {
		// arrays / primitives are not objects per parseJsonObject — falls back to plain text
		expect(plainTextContext({ exitCode: 0, stdout: "[1,2,3]", stderr: "", timedOut: false })).toBe("[1,2,3]");
	});

	it("returns undefined on empty stdout", () => {
		expect(plainTextContext({ exitCode: 0, stdout: "   ", stderr: "", timedOut: false })).toBeUndefined();
	});
});
