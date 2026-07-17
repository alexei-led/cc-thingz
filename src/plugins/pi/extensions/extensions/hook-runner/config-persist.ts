/**
 * Filesystem read/write helpers for hooks config files.
 */

import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname } from "node:path";

import { projectHooksConfigPath } from "./config-paths.js";
import { extractHookRunnerOptions } from "./config-parse.js";
import type { HookRunnerOptions } from "./types.js";

export function writeHooksConfig(path: string, parsed: Record<string, unknown>): void {
	mkdirSync(dirname(path), { recursive: true });
	writeFileSync(path, JSON.stringify(parsed, null, 2) + "\n", "utf-8");
}

export function readHookRunnerOptions(path: string): HookRunnerOptions {
	try {
		const raw = readFileSync(path, "utf-8");
		const parsed = JSON.parse(raw) as unknown;
		return extractHookRunnerOptions(parsed);
	} catch {
		return {};
	}
}

export function readProjectHookRunnerOptions(cwd: string): HookRunnerOptions {
	return readHookRunnerOptions(projectHooksConfigPath(cwd));
}

/** existsSync wrapper for callers that want to check before reading. */
export function pathExists(path: string): boolean {
	return existsSync(path);
}
