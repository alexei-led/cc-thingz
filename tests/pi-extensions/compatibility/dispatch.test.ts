import { describe, expect, it } from "bun:test";

import { buildTelemetryLine, classifyExecResult, extractProgress, HOOK_OUTPUT_MAX_BYTES } from "../../../src/plugins/pi/extensions/extensions/hook-runner/dispatch.ts";
import type { HookEntryRuntime, HookRunResult } from "../../../src/plugins/pi/extensions/extensions/hook-runner/types.ts";

describe("extractProgress", () => {
	it("returns stderr unchanged when no progress markers present", () => {
		expect(extractProgress("normal stderr output").stderr).toBe("normal stderr output");
	});

	it("strips progress lines from stderr", () => {
		const stderr = ["starting", "^^PROGRESS 10 reading input", "more noise", "^^PROGRESS 50 halfway", "^^PROGRESS 100 done", "trailer"].join("\n");
		expect(extractProgress(stderr).stderr).toBe(["starting", "more noise", "trailer"].join("\n"));
	});

	it("leaves malformed progress markers in stderr", () => {
		expect(extractProgress("^^PROGRESS notanumber message").stderr).toContain("^^PROGRESS notanumber");
	});

	it("handles CRLF line endings", () => {
		expect(extractProgress("step1\r\n^^PROGRESS 25 quarter\r\nstep2").stderr).toBe("step1\nstep2");
	});
});

describe("buildTelemetryLine", () => {
	const fixedNow = () => new Date("2026-05-14T20:00:00.000Z");

	it("uses the entry's event name, not the command path", () => {
		// Regression: telemetry once wrote `entry.config.command` as the event,
		// burying every hook run under its script path instead of `PreToolUse`.
		const entry: HookEntryRuntime = {
			config: { type: "command", command: "/abs/path/to/script.py", timeout: 30 },
			source: "bundled",
			disabled: false,
			eventName: "PreToolUse",
		};
		const result: HookRunResult = { exitCode: 0, stdout: "", stderr: "", timedOut: false };

		const line = buildTelemetryLine(entry, result, 42, fixedNow);
		const parsed = JSON.parse(line) as Record<string, unknown>;
		expect(parsed.event).toBe("PreToolUse");
		expect(parsed.hook).toBe("script.py");
		expect(parsed.source).toBe("bundled");
		expect(parsed.exit_code).toBe(0);
		expect(parsed.duration_ms).toBe(42);
		expect(parsed.timed_out).toBe(false);
		expect(parsed.ts).toBe("2026-05-14T20:00:00.000Z");
	});

	it("preserves the timed_out and exit_code signals", () => {
		const entry: HookEntryRuntime = {
			config: { type: "command", command: "/x/y" },
			source: "global",
			disabled: false,
			eventName: "Stop",
		};
		const line = buildTelemetryLine(entry, { exitCode: 124, stdout: "", stderr: "kill", timedOut: true }, 1, fixedNow);
		const parsed = JSON.parse(line) as { event: string; timed_out: boolean; exit_code: number };
		expect(parsed.event).toBe("Stop");
		expect(parsed.timed_out).toBe(true);
		expect(parsed.exit_code).toBe(124);
	});

	it("truncates stderr to STDERR_HEAD_LIMIT", () => {
		const entry: HookEntryRuntime = {
			config: { type: "command", command: "/x/loud.py" },
			source: "project",
			disabled: false,
			eventName: "PostToolUse",
		};
		const noisy = "x".repeat(2000);
		const line = buildTelemetryLine(entry, { exitCode: 1, stdout: "", stderr: noisy, timedOut: false }, 5, fixedNow);
		const parsed = JSON.parse(line) as { stderr_head: string };
		expect(parsed.stderr_head.length).toBeLessThanOrEqual(500);
	});
});

// ---------------------------------------------------------------------------
// classifyExecResult — pure translation of the execFile callback shape into
// the canonical HookRunResult. Mocking child_process at the suite level (see
// hook-runner.test.ts) blocks real-subprocess assertions, so the branches are
// tested directly via this extracted function.
// ---------------------------------------------------------------------------

describe("classifyExecResult", () => {
	it("flags timed_out=true when the child was killed by the timeout", () => {
		const err = Object.assign(new Error("timeout"), { killed: true, code: undefined });
		const result = classifyExecResult(err, "", "child stderr");
		expect(result.timedOut).toBe(true);
		// Numeric exit code is absent on timeout; fallback is 1.
		expect(result.exitCode).toBe(1);
		expect(result.stderr).toBe("child stderr");
	});

	it("collapses maxBuffer overflow into exit 2 with the cap notice", () => {
		const err = Object.assign(new Error("stdout maxBuffer length exceeded"), {
			code: "ERR_CHILD_PROCESS_STDIO_MAXBUFFER",
		});
		const result = classifyExecResult(err, "huge", "noise");
		expect(result.exitCode).toBe(2);
		expect(result.timedOut).toBe(false);
		expect(result.stderr.startsWith(`Hook output exceeded ${HOOK_OUTPUT_MAX_BYTES / (1024 * 1024)}MB cap`)).toBe(true);
		// Existing stderr is preserved after the cap notice for debugging.
		expect(result.stderr).toContain("noise");
	});

	it("uses the bare cap notice when stderr is empty at overflow", () => {
		const err = Object.assign(new Error("overflow"), { code: "ERR_CHILD_PROCESS_STDIO_MAXBUFFER" });
		const result = classifyExecResult(err, "", "");
		expect(result.exitCode).toBe(2);
		expect(result.stderr).toBe(`Hook output exceeded ${HOOK_OUTPUT_MAX_BYTES / (1024 * 1024)}MB cap`);
	});

	it("propagates a numeric exit code as the result code", () => {
		const err = Object.assign(new Error("blocked"), { code: 2, killed: false });
		const result = classifyExecResult(err, "out", "blocked by hook");
		expect(result.exitCode).toBe(2);
		expect(result.timedOut).toBe(false);
		expect(result.stderr).toBe("blocked by hook");
	});

	it("returns exit 0 + clean stderr when the child succeeds", () => {
		const result = classifyExecResult(null, "{}", "");
		expect(result.exitCode).toBe(0);
		expect(result.stdout).toBe("{}");
		expect(result.timedOut).toBe(false);
	});

	it("falls back to exit 1 when err.code is missing", () => {
		const err = new Error("opaque");
		const result = classifyExecResult(err, "", "boom");
		expect(result.exitCode).toBe(1);
		expect(result.timedOut).toBe(false);
	});
});
