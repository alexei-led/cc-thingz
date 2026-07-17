/**
 * Hook-runner configuration: in-memory cache + the `loadConfig` orchestrator.
 *
 * Pure helpers live in sibling files:
 *  - `config-paths.ts`    — path resolution constants
 *  - `config-parse.ts`    — normalisation, tagging, merge
 *  - `config-package.ts`  — package-contributed hooks + validation
 *  - `config-persist.ts`  — fs read/write helpers
 *  - `config-summary.ts`  — `/hooks` render helpers
 *
 * This file re-exports the public surface and owns the lazy-loaded cache,
 * keyed by cwd. The cache is process-local — Pi reuses the same Node runtime
 * across sessions.
 */

import { readFileSync } from "node:fs";
import { join } from "node:path";

import { agentDir, BUNDLED_HOOKS_CONFIG_PATH, FORCED_RELOAD_DEBOUNCE_MS } from "./config-paths.js";
import {
	applyDisabled,
	extractHookRunnerOptions,
	extractHooksConfig,
	filterEnabled,
	hasUnsupportedIfPredicate,
	mergeHooks,
	resolveBundledHookPaths,
	tagEntries,
} from "./config-parse.js";
import { discoverPackageHookContributions } from "./config-package.js";
import type { HooksConfig, HookSource } from "./types.js";

// ---------------------------------------------------------------------------
// Public re-exports (preserve external import path `./config.js`)
// ---------------------------------------------------------------------------

export {
	agentDir,
	BUNDLED_HOOKS_CONFIG_PATH,
	FORCED_RELOAD_DEBOUNCE_MS,
	globalHooksConfigPath,
	HOOKS_DIR,
	PI_HOOKS_DIR_PLACEHOLDER,
	PKG_DIR_PLACEHOLDER,
	projectHooksConfigPath,
} from "./config-paths.js";
export { basename } from "./config-parse.js";
export { discoverPackageHookContributions, parsePackageContribution, validatePackageCommand } from "./config-package.js";
export { pathExists, readHookRunnerOptions, readProjectHookRunnerOptions, writeHooksConfig } from "./config-persist.js";
export { hooksSummary, listAllHookNames } from "./config-summary.js";
export type { HookNameEntry } from "./config-summary.js";

// ---------------------------------------------------------------------------
// Module state
// ---------------------------------------------------------------------------

let _config: HooksConfig | null = null;
/** Pre-filter view (disabled entries still present) — used for /hooks summary. */
let _configRaw: HooksConfig | null = null;
let _configLoadedForCwd = "";
let _ifWarningShown = false;
let _lastForcedReloadMs = 0;
let _bundledCache: HooksConfig | null = null;

export function _resetForTesting(): void {
	_config = null;
	_configRaw = null;
	_configLoadedForCwd = "";
	_ifWarningShown = false;
	_lastForcedReloadMs = 0;
	_bundledCache = null;
}

function loadBundledHooksConfig(): HooksConfig {
	if (_bundledCache) return _bundledCache;
	try {
		const raw = readFileSync(BUNDLED_HOOKS_CONFIG_PATH, "utf-8");
		const parsed = JSON.parse(raw) as unknown;
		const bundled = extractHooksConfig(parsed, BUNDLED_HOOKS_CONFIG_PATH);
		_bundledCache = resolveBundledHookPaths(bundled);
	} catch {
		_bundledCache = {};
	}
	return _bundledCache;
}

// ---------------------------------------------------------------------------
// Public API — load + accessors
// ---------------------------------------------------------------------------

export function loadConfig(cwd: string, force = false): void {
	if (!force && _config && _configLoadedForCwd === cwd) return;
	_configLoadedForCwd = cwd;

	const globalAgentDir = agentDir();
	const configPaths: Array<{ path: string; source: HookSource }> = [
		{ path: join(globalAgentDir, "settings.json"), source: "global" },
		{ path: join(globalAgentDir, "hooks.json"), source: "global" },
		{ path: join(cwd, ".pi", "settings.json"), source: "project" },
		{ path: join(cwd, ".pi", "hooks.json"), source: "project" },
	];

	let disableBundledHooks = false;
	const disabledNames = new Set<string>();
	const hookConfigs: Array<{ config: HooksConfig; source: HookSource }> = [];

	for (const { path: configPath, source } of configPaths) {
		try {
			const raw = readFileSync(configPath, "utf-8");
			const parsed = JSON.parse(raw) as unknown;
			const options = extractHookRunnerOptions(parsed);
			if (typeof options.disableBundledHooks === "boolean") {
				disableBundledHooks = options.disableBundledHooks;
			}
			if (options.disabledHooks) {
				for (const name of options.disabledHooks) disabledNames.add(name);
			}
			const hooksConfig = extractHooksConfig(parsed, configPath);
			if (Object.keys(hooksConfig).length > 0) {
				hookConfigs.push({ config: hooksConfig, source });
			}
		} catch {
			// File absent or malformed: silently skip
		}
	}

	const base = disableBundledHooks ? {} : tagEntries(loadBundledHooksConfig(), "bundled");

	// Plugin-contributed hooks land between bundled and user configs: user
	// configs still win on conflict, but plugins can extend the default set
	// without cc-thingz edits.
	const packageContributions = discoverPackageHookContributions();
	if (Object.keys(packageContributions).length > 0) {
		mergeHooks(base, tagEntries(packageContributions, "package"));
	}

	for (const { config, source } of hookConfigs) {
		mergeHooks(base, tagEntries(config, source));
		if (_ifWarningShown) continue;
		if (hasUnsupportedIfPredicate(config)) {
			_ifWarningShown = true;
			console.warn("[hook-runner] 'if' predicate in hooks config is not supported in v1; use 'matcher' instead");
		}
	}

	applyDisabled(base, disabledNames);
	_configRaw = base;
	_config = filterEnabled(base);
}

/**
 * Debounced force-reload trigger — used by the ConfigChange synthetic-hook
 * path so repeated config writes don't thrash the disk.
 */
export function shouldForceReloadForConfigChange(): boolean {
	const now = Date.now();
	if (now - _lastForcedReloadMs >= FORCED_RELOAD_DEBOUNCE_MS) {
		_lastForcedReloadMs = now;
		return true;
	}
	return false;
}

export function resolvedConfig(): HooksConfig {
	return _config ?? loadBundledHooksConfig();
}

export function rawConfig(): HooksConfig {
	return _configRaw ?? loadBundledHooksConfig();
}
