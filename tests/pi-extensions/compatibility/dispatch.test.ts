import { describe, expect, it } from "bun:test";

import { buildTelemetryLine, extractProgress } from "../../../src/plugins/pi/extensions/extensions/hook-runner/dispatch.ts";
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
