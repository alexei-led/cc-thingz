import { execFileSync } from "node:child_process";
import { describe, expect, it, spyOn } from "bun:test";
import { existsSync, mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { cancelRunningHooks, runHook, runShutdownHookAsync } from "../../../src/plugins/pi/extensions/extensions/hook-runner/dispatch.ts";
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

function isRunning(pid: number): boolean {
	if (!isAlive(pid)) return false;
	try {
		// Orphans can remain zombies until PID 1 reaps them; they have exited.
		return !execFileSync("ps", ["-o", "stat=", "-p", String(pid)], { encoding: "utf8" })
			.trim()
			.startsWith("Z");
	} catch (error) {
		if (!isAlive(pid)) return false;
		throw error;
	}
}

describe("async SessionEnd — independent supervisor", () => {
	it("survives the launching process exiting and delivers stdin", async () => {
		const dir = mkdtempSync(join(tmpdir(), "hook-runner-shutdown-"));
		const output = join(dir, "result");
		try {
			const entry = makeEntry(`sleep 2; cat > "${output}.tmp"; mv "${output}.tmp" "${output}"`, 10);
			const modulePath = join(process.cwd(), "src/plugins/pi/extensions/extensions/hook-runner/dispatch.ts");
			const code = `import { runShutdownHookAsync } from ${JSON.stringify(modulePath)}; runShutdownHookAsync(${JSON.stringify(entry)}, '{"end_reason":"quit"}');`;
			execFileSync(process.execPath, ["-e", code], { timeout: 1500 });
			const deadline = Date.now() + 10000;
			while (!existsSync(output) && Date.now() < deadline) await Bun.sleep(20);
			expect(readFileSync(output, "utf8")).toBe('{"end_reason":"quit"}');
		} finally {
			rmSync(dir, { recursive: true, force: true });
		}
	}, 15000);

	it("reports missing Node without blocking or leaving a hook process", async () => {
		const dir = mkdtempSync(join(tmpdir(), "hook-runner-no-node-"));
		const output = join(dir, "unexpected");
		const originalPath = process.env.PATH;
		let notified = () => {};
		const reported = new Promise<void>((resolve) => {
			notified = resolve;
		});
		const errorSpy = spyOn(console, "error").mockImplementation(() => notified());
		try {
			process.env.PATH = dir;
			runShutdownHookAsync(makeEntry(`echo launched > "${output}"`, 2), "{}");
			await reported;
			expect(errorSpy).toHaveBeenCalledWith("[hook-runner] Could not start async SessionEnd hook");
			expect(existsSync(output)).toBe(false);
		} finally {
			if (originalPath === undefined) delete process.env.PATH;
			else process.env.PATH = originalPath;
			errorSpy.mockRestore();
			rmSync(dir, { recursive: true, force: true });
		}
	}, 5000);

	it("enforces its own timeout and kills SIGTERM-trapping descendants", async () => {
		const dir = mkdtempSync(join(tmpdir(), "hook-runner-shutdown-tree-"));
		const pidFile = join(dir, "pid");
		let pid: number | undefined;
		try {
			runShutdownHookAsync(makeEntry(`bash -c 'trap "" TERM; echo $$ > "${pidFile}"; exec sleep 30' & wait`, 3), "{}");
			const readyDeadline = Date.now() + 2000;
			while (!existsSync(pidFile) && Date.now() < readyDeadline) await Bun.sleep(10);
			pid = Number(readFileSync(pidFile, "utf8").trim());
			expect(pid).toBeGreaterThan(0);
			const deadline = Date.now() + 7000;
			while (isRunning(pid) && Date.now() < deadline) await Bun.sleep(50);
			let status = "";
			try {
				status = execFileSync("ps", ["-o", "stat=", "-p", String(pid)], { encoding: "utf8" }).trim();
			} catch {}
			expect(status === "" || status.startsWith("Z")).toBe(true);
		} finally {
			if (pid && isAlive(pid)) {
				try {
					process.kill(pid, "SIGKILL");
				} catch {}
			}
			rmSync(dir, { recursive: true, force: true });
		}
	}, 12000);
});

describe("runHook — real subprocess timeout kill", () => {
	it("force-kills a SIGTERM-trapping child near the deadline instead of waiting for it to finish", async () => {
		const dir = mkdtempSync(join(tmpdir(), "hook-runner-timeout-"));
		const pidFile = join(dir, "pid");
		try {
			// The child sleeps far longer than the 1s deadline so a kill that's
			// merely late under CPU load still lands well short of the child's
			// own exit — a slow force-kill can't be mistaken for a natural one.
			const entry = makeEntry(`echo $$ > ${pidFile}; trap '' TERM; echo out; sleep 30`, 1);

			const start = Date.now();
			const result = await runHook(entry, "");
			const elapsed = Date.now() - start;

			expect(result.timedOut).toBe(true);
			expect(result.exitCode).toBe(1);
			expect(elapsed).toBeLessThanOrEqual(8000);

			const pid = Number(readFileSync(pidFile, "utf8").trim());
			expect(Number.isNaN(pid)).toBe(false);

			const deadline = Date.now() + 3000;
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
	}, 15000);

	it.each(["timeout", "abort", "shutdown"])(
		"terminates descendants on %s even after the shell exits",
		async (mode) => {
			const dir = mkdtempSync(join(tmpdir(), "hook-runner-tree-"));
			const pidFile = join(dir, "child-pid");
			const controller = new AbortController();
			let pid: number | undefined;
			try {
				// "timeout" mode's own deadline must stay well clear of the poll
				// below that waits for the child to report in: under CPU load a
				// tight deadline can force-kill the process tree before the pid
				// file is even written, racing the readiness check below it.
				const timeoutSec = mode === "timeout" ? 6 : 10;
				const entry = makeEntry(`bash -c 'trap "" TERM; echo $$ > "${pidFile}"; exec sleep 30' </dev/null >/dev/null 2>&1 & wait`, timeoutSec);
				const pending = runHook(entry, "", { signal: controller.signal });
				const readyDeadline = Date.now() + (timeoutSec * 1000) / 2;
				while (!existsSync(pidFile) && Date.now() < readyDeadline) await Bun.sleep(10);
				expect(existsSync(pidFile)).toBe(true);
				pid = Number(readFileSync(pidFile, "utf8").trim());
				expect(pid).toBeGreaterThan(0);
				if (mode === "abort") controller.abort();
				if (mode === "shutdown") await cancelRunningHooks();
				const result = await pending;
				expect(result.exitCode).toBe(mode === "timeout" ? 1 : 2);
				expect(result.timedOut).toBe(mode === "timeout");
				const deadline = Date.now() + 3000;
				while (isRunning(pid) && Date.now() < deadline) await Bun.sleep(50);
				let status = "";
				try {
					status = execFileSync("ps", ["-o", "stat=", "-p", String(pid)], { encoding: "utf8" }).trim();
				} catch {}
				expect(status === "" || status.startsWith("Z")).toBe(true);
			} finally {
				controller.abort();
				if (pid && isAlive(pid)) {
					try {
						process.kill(pid, "SIGKILL");
					} catch {}
				}
				rmSync(dir, { recursive: true, force: true });
			}
		},
		20000,
	);

	it("does not launch a pre-cancelled hook", async () => {
		const result = await runHook(makeEntry("echo should-not-run", 1), "", { signal: AbortSignal.abort() });
		expect(result.exitCode).toBe(2);
		expect(result.stdout).toBe("");
		expect(result.stderr).toContain("cancelled");
	});

	it("caps real stdout and denies overflowing hooks", async () => {
		// Asserts the byte cap, not latency: a generous entry timeout keeps a
		// CPU-starved run from being killed by the deadline instead of the cap.
		const result = await runHook(makeEntry("head -c 12000000 /dev/zero", 15), "");
		expect(result.exitCode).toBe(2);
		expect(result.stdout.length).toBeLessThanOrEqual(10 * 1024 * 1024);
		expect(result.stderr).toContain("cap");
		expect(result.timedOut).toBe(false);
	}, 16000);

	it("preserves hook stdin, stderr and blocking exit codes", async () => {
		// Asserts exit-code/stream plumbing, not latency: a generous entry
		// timeout keeps this from racing a CPU-starved runner.
		const result = await runHook(makeEntry("cat; echo denied >&2; exit 2", 10), '{"event":"test"}');
		expect(result).toEqual({ exitCode: 2, stdout: '{"event":"test"}', stderr: "denied\n", timedOut: false });
	}, 12000);

	it("rejects invalid timeouts without launching", async () => {
		const result = await runHook(makeEntry("echo should-not-run", -1), "");
		expect(result.exitCode).toBe(2);
		expect(result.stdout).toBe("");
	});

	it("happy path is unaffected: a fast hook resolves quickly with exitCode 0", async () => {
		// The behavior under test is "didn't wait for the timeout", not raw
		// latency: the entry timeout is generous, and the elapsed bound only
		// needs to stay comfortably under it to prove the deadline was never hit.
		const entry = makeEntry("echo hello", 10);

		const start = Date.now();
		const result = await runHook(entry, "");
		const elapsed = Date.now() - start;

		expect(result.exitCode).toBe(0);
		expect(result.timedOut).toBe(false);
		expect(result.stdout.trim()).toBe("hello");
		expect(elapsed).toBeLessThan(5000);
	}, 12000);
});
