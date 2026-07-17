// Real-subprocess regression coverage for the timeout/SIGKILL fallback in
// `runHook`. Deliberately does NOT mock `node:child_process` — hook-runner.test.ts
// installs a process-wide `mock.module("node:child_process", ...)` that would
// make these assertions meaningless if it leaked into this suite. This file
// must run under `bun test --isolate` (see Makefile) so that mock never loads.
//
// Bug being pinned: execFile's own `timeout` sends SIGTERM at the deadline. A
// child that traps SIGTERM never exits, so execFile's callback never fires and
// runHook hung until the child's own workload finished — here, ~5s — instead
// of bailing out near the configured timeout.

import { describe, expect, it } from "bun:test";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { runHook } from "../../../src/plugins/pi/extensions/extensions/hook-runner/dispatch.ts";
import type { HookEntryRuntime } from "../../../src/plugins/pi/extensions/extensions/hook-runner/types.ts";

function makeEntry(command: string, timeoutSec: number): HookEntryRuntime {
	return {
		config: { type: "command", command, timeout: timeoutSec },
		source: "bundled",
		disabled: false,
		eventName: "Stop",
	};
}

function isAlive(pid: number): boolean {
	try {
		process.kill(pid, 0);
		return true;
	} catch {
		return false;
	}
}

describe("runHook — real subprocess timeout kill", () => {
	it("force-kills a SIGTERM-trapping child near the deadline instead of waiting for it to finish", async () => {
		const dir = mkdtempSync(join(tmpdir(), "hook-runner-timeout-"));
		const pidFile = join(dir, "pid");
		try {
			// The child records its own pid ($$, i.e. the `bash` process execFile
			// spawns directly — no intermediate shell layer), ignores SIGTERM, then
			// sleeps far longer than the 1s timeout so the regression is unambiguous.
			const entry = makeEntry(`echo $$ > ${pidFile}; trap '' TERM; echo out; sleep 5`, 1);

			const start = Date.now();
			const result = await runHook(entry, "");
			const elapsed = Date.now() - start;

			expect(result.timedOut).toBe(true);
			expect(result.exitCode).toBe(1);
			// Pre-fix this resolves ~5000ms (waits for `sleep 5`). Post-fix it
			// resolves at ~timeout(1s) + KILL_GRACE_MS(1.5s), well under 5s.
			expect(elapsed).toBeLessThanOrEqual(4000);

			const pid = Number(readFileSync(pidFile, "utf8").trim());
			expect(Number.isNaN(pid)).toBe(false);

			// SIGKILL delivery/reaping isn't instantaneous — poll briefly.
			const deadline = Date.now() + 1000;
			while (isAlive(pid) && Date.now() < deadline) {
				await new Promise((r) => setTimeout(r, 20));
			}

			let killError: NodeJS.ErrnoException | undefined;
			try {
				process.kill(pid, 0);
			} catch (err) {
				killError = err as NodeJS.ErrnoException;
			}
			expect(killError).toBeDefined();
			expect(killError?.code).toBe("ESRCH");
		} finally {
			rmSync(dir, { recursive: true, force: true });
		}
	}, 8000);

	it("happy path is unaffected: a fast hook resolves quickly with exitCode 0", async () => {
		const entry = makeEntry("echo hello", 5);

		const start = Date.now();
		const result = await runHook(entry, "");
		const elapsed = Date.now() - start;

		expect(result.exitCode).toBe(0);
		expect(result.timedOut).toBe(false);
		expect(result.stdout.trim()).toBe("hello");
		// Proves the fallback kill timer was cleared on the normal settle path —
		// if it weren't, it would still fire ~6.5s later (timeout 5s + grace 1.5s).
		expect(elapsed).toBeLessThan(1000);
	});
});
