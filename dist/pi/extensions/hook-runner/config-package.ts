/**
 * Discovery and validation of package-contributed hooks.
 *
 * Pi packages may declare `cc-thingz.hooks` in their `package.json` to register
 * hooks without editing cc-thingz. Each contributed command must be an absolute
 * path resolved inside the package's directory and free of shell metacharacters.
 */

import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { join, resolve as resolvePath } from "node:path";

import { agentDir, PKG_DIR_PLACEHOLDER } from "./config-paths.js";
import { mergeHooks, normalizeHookConfig } from "./config-parse.js";
import type { HookEntryRuntime, HookGroup, HooksConfig } from "./types.js";
import { isRecord } from "./types.js";

// Shell metacharacters that change interpretation when passed to `bash -c`.
// Plugin-contributed commands run inside the user's shell so any of these is
// a potential injection vector from a malicious package. Newlines and
// carriage returns are included because `bash -c` happily executes every
// line of a multiline argument; without them, a package.json string like
// "/pkg/safe.sh\nrm -rf ~" would split into two commands and the second
// would run despite the first-token path check.
const PACKAGE_CMD_FORBIDDEN_RE = /[;&|<>`$()\\{}\n\r]/;

/**
 * Validate a package-contributed hook command.
 *
 * Returns the resolved command string when safe, or `undefined` when the
 * command would escape the package's directory or contain shell metachars.
 * Plugin authors can use `${PKG_DIR}` as a stand-in for the package root;
 * everything else must be an absolute path that resolves inside `repoDir`.
 */
export function validatePackageCommand(command: string, repoDir: string): string | undefined {
	if (typeof command !== "string") return undefined;
	const substituted = command.replaceAll(PKG_DIR_PLACEHOLDER, repoDir);
	const trimmed = substituted.trim();
	if (!trimmed) return undefined;
	if (PACKAGE_CMD_FORBIDDEN_RE.test(substituted)) return undefined;
	const firstToken = trimmed.split(/\s+/)[0] ?? "";
	if (!firstToken.startsWith("/")) return undefined;
	const repoAbs = resolvePath(repoDir);
	const cmdAbs = resolvePath(firstToken);
	if (cmdAbs !== repoAbs && !cmdAbs.startsWith(repoAbs + "/")) return undefined;
	return substituted;
}

function sanitisePackageContribution(config: HooksConfig, repoDir: string): HooksConfig {
	const out: HooksConfig = {};
	for (const [eventName, groups] of Object.entries(config)) {
		if (!groups) continue;
		const cleanGroups: HookGroup[] = [];
		for (const group of groups) {
			const cleanHooks: HookEntryRuntime[] = [];
			for (const entry of group.hooks) {
				const safe = validatePackageCommand(entry.config.command, repoDir);
				if (!safe) continue;
				cleanHooks.push({
					...entry,
					config: { ...entry.config, command: safe },
				});
			}
			if (cleanHooks.length === 0) continue;
			cleanGroups.push({ matcher: group.matcher, hooks: cleanHooks });
		}
		if (cleanGroups.length > 0) out[eventName] = cleanGroups;
	}
	return out;
}

/**
 * Parse a `package.json` body looking for `cc-thingz.hooks` contributions.
 *
 * When `repoDir` is provided, every contributed command must either be an
 * absolute path inside `repoDir` or use the `${PKG_DIR}` placeholder; commands
 * with shell metacharacters are rejected. When `repoDir` is omitted the parser
 * skips path validation — useful for round-trip parsing in tooling tests but
 * never the path taken at runtime.
 */
export function parsePackageContribution(packageJsonContent: string, repoDir?: string): HooksConfig | undefined {
	try {
		const parsed = JSON.parse(packageJsonContent) as unknown;
		if (!isRecord(parsed)) return undefined;
		const ccThingz = parsed["cc-thingz"];
		if (!isRecord(ccThingz)) return undefined;
		const hooks = ccThingz.hooks;
		if (!isRecord(hooks)) return undefined;
		const normalized = normalizeHookConfig(hooks);
		if (repoDir === undefined) return normalized;
		const cleaned = sanitisePackageContribution(normalized, repoDir);
		return Object.keys(cleaned).length > 0 ? cleaned : undefined;
	} catch {
		return undefined;
	}
}

function safeIsDirectory(path: string): boolean {
	try {
		return statSync(path).isDirectory();
	} catch {
		return false;
	}
}

function readPackageContribution(repoDir: string): HooksConfig | undefined {
	const manifest = join(repoDir, "package.json");
	if (!existsSync(manifest)) return undefined;
	try {
		const raw = readFileSync(manifest, "utf-8");
		return parsePackageContribution(raw, repoDir);
	} catch {
		return undefined;
	}
}

/**
 * Scan installed Pi packages for hook contributions.
 *
 * Layout: Pi installs each git package under `~/.pi/agent/git/<host>/<org>/<repo>/`,
 * so we look three levels deep from `agentDir()/git/`. Errors during scan
 * are silently swallowed — a misshapen package.json must never break
 * session_start.
 */
export function discoverPackageHookContributions(): HooksConfig {
	const base = join(agentDir(), "git");
	if (!existsSync(base)) return {};
	const merged: HooksConfig = {};
	try {
		for (const host of readdirSync(base)) {
			const hostDir = join(base, host);
			if (!safeIsDirectory(hostDir)) continue;
			for (const org of readdirSync(hostDir)) {
				const orgDir = join(hostDir, org);
				if (!safeIsDirectory(orgDir)) continue;
				for (const repo of readdirSync(orgDir)) {
					const repoDir = join(orgDir, repo);
					if (!safeIsDirectory(repoDir)) continue;
					const contributed = readPackageContribution(repoDir);
					if (contributed) {
						mergeHooks(merged, contributed);
					}
				}
			}
		}
	} catch {
		// Best-effort scan.
	}
	return merged;
}
