import { execFileSync } from "node:child_process";
import { describe, expect, it } from "bun:test";
import { existsSync, mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { cancelRunningHooks, runHook } from "../../../src/plugins/pi/extensions/extensions/hook-runner/dispatch.ts";
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
			const entry = makeEntry(`echo $$ > ${pidFile}; trap '' TERM; echo out; sleep 5`, 1);

			const start = Date.now();
			const result = await runHook(entry, "");
			const elapsed = Date.now() - start;

			expect(result.timedOut).toBe(true);
			expect(result.exitCode).toBe(1);
			expect(elapsed).toBeLessThanOrEqual(4000);

			const pid = Number(readFileSync(pidFile, "utf8").trim());
			expect(Number.isNaN(pid)).toBe(false);

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

	it.each(["timeout", "abort", "shutdown"])("terminates descendants on %s even after the shell exits", async (mode) => {
		const dir = mkdtempSync(join(tmpdir(), "hook-runner-tree-"));
		const pidFile = join(dir, "child-pid");
		const controller = new AbortController();
		let pid: number | undefined;
		try {
			const entry = makeEntry(`bash -c 'trap "" TERM; echo $$ > "${pidFile}"; exec sleep 30' </dev/null >/dev/null 2>&1 & wait`, mode === "timeout" ? 0.3 : 10);
			const pending = runHook(entry, "", { signal: controller.signal });
			const readyDeadline = Date.now() + 2000;
			while (!existsSync(pidFile) && Date.now() < readyDeadline) await Bun.sleep(10);
			expect(existsSync(pidFile)).toBe(true);
			pid = Number(readFileSync(pidFile, "utf8").trim());
			expect(pid).toBeGreaterThan(0);
			if (mode === "abort") controller.abort();
			if (mode === "shutdown") await cancelRunningHooks();
			const result = await pending;
			expect(result.exitCode).toBe(mode === "timeout" ? 1 : 2);
			expect(result.timedOut).toBe(mode === "timeout");
			const deadline = Date.now() + 1000;
			while (isAlive(pid) && Date.now() < deadline) await Bun.sleep(20);
			let status = "";
			try { status = execFileSync("ps", ["-o", "stat=", "-p", String(pid)], { encoding: "utf8" }).trim(); } catch {}
			expect(status === "" || status.startsWith("Z")).toBe(true);
		} finally {
			controller.abort();
			if (pid && isAlive(pid)) {
				try { process.kill(pid, "SIGKILL"); } catch {}
			}
			rmSync(dir, { recursive: true, force: true });
		}
	}, 6000);

	it("does not launch a pre-cancelled hook", async () => {
		const result = await runHook(makeEntry("echo should-not-run", 1), "", { signal: AbortSignal.abort() });
		expect(result.exitCode).toBe(2);
		expect(result.stdout).toBe("");
		expect(result.stderr).toContain("cancelled");
	});

	it("caps real stdout and denies overflowing hooks", async () => {
		const result = await runHook(makeEntry("head -c 12000000 /dev/zero", 5), "");
		expect(result.exitCode).toBe(2);
		expect(result.stdout.length).toBeLessThanOrEqual(10 * 1024 * 1024);
		expect(result.stderr).toContain("cap");
		expect(result.timedOut).toBe(false);
	}, 6000);

	it("preserves hook stdin, stderr and blocking exit codes", async () => {
		const result = await runHook(makeEntry("cat; echo denied >&2; exit 2", 2), '{"event":"test"}');
		expect(result).toEqual({ exitCode: 2, stdout: '{"event":"test"}', stderr: "denied\n", timedOut: false });
	});

	it("rejects invalid timeouts without launching", async () => {
		const result = await runHook(makeEntry("echo should-not-run", -1), "");
		expect(result.exitCode).toBe(2);
		expect(result.stdout).toBe("");
	});

	it("happy path is unaffected: a fast hook resolves quickly with exitCode 0", async () => {
		const entry = makeEntry("echo hello", 5);

		const start = Date.now();
		const result = await runHook(entry, "");
		const elapsed = Date.now() - start;

		expect(result.exitCode).toBe(0);
		expect(result.timedOut).toBe(false);
		expect(result.stdout.trim()).toBe("hello");
		expect(elapsed).toBeLessThan(1000);
	});
});
