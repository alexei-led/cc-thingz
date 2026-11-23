import { afterEach, describe, expect, it, mock } from "bun:test";
import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

mock.module("@earendil-works/pi-coding-agent", () => ({ CONFIG_DIR_NAME: ".pi" }));
const { configureAutomaticTests } = await import("../../src/plugins/pi/extensions/extensions/hook-runner/automatic-tests.ts");

describe("automatic tests project setting", () => {
	const original = process.env.SKIP_TESTS;
	afterEach(() => {
		if (original === undefined) delete process.env.SKIP_TESTS;
		else process.env.SKIP_TESTS = original;
	});

	it("enables only for an explicitly opted-in trusted project", () => {
		const cwd = mkdtempSync(join(tmpdir(), "automatic-tests-"));
		const run = (trusted: boolean) => configureAutomaticTests({ cwd, isProjectTrusted: () => trusted });
		try {
			run(true);
			expect(process.env.SKIP_TESTS).toBe("1");
			mkdirSync(join(cwd, ".pi"));
			writeFileSync(join(cwd, ".pi", "settings.json"), '{"automaticTests":true}');
			run(true);
			expect(process.env.SKIP_TESTS).toBe("0");
			run(false);
			expect(process.env.SKIP_TESTS).toBe("1");
			writeFileSync(join(cwd, ".pi", "settings.json"), "{invalid");
			run(true);
			expect(process.env.SKIP_TESTS).toBe("1");
		} finally {
			rmSync(cwd, { recursive: true, force: true });
		}
	});
});
