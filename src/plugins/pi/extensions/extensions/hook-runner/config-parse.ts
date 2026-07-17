/**
 * Pure parsing, normalisation, tagging, and merge helpers for hooks config.
 * No fs access, no module state — safe to call from any layer.
 */

import type { HookEntryConfig, HookEntryRuntime, HookGroup, HookRunnerOptions, HooksConfig, HookSource } from "./types.js";
import { isRecord } from "./types.js";
import { HOOKS_DIR, PI_HOOKS_DIR_PLACEHOLDER } from "./config-paths.js";

export function normalizeHookConfig(raw: unknown): HooksConfig {
	if (!isRecord(raw)) return {};
	const normalized: HooksConfig = {};
	for (const [key, groups] of Object.entries(raw)) {
		if (key === "hookRunner") continue;
		if (!Array.isArray(groups)) continue;
		const validGroups: HookGroup[] = [];
		for (const group of groups) {
			if (!isRecord(group)) continue;
			if (!Array.isArray(group.hooks)) continue;
			const validEntries: HookEntryRuntime[] = [];
			for (const entry of group.hooks) {
				if (!isRecord(entry) || typeof entry.command !== "string") continue;
				const config: HookEntryConfig = {
					type: "command",
					command: entry.command,
				};
				if (typeof entry.timeout === "number") config.timeout = entry.timeout;
				if (typeof entry.async === "boolean") config.async = entry.async;
				// Source/disabled are filled in later by tagEntries / applyDisabled.
				validEntries.push({ config, source: "bundled", disabled: false, eventName: key });
			}
			if (validEntries.length === 0) continue;
			validGroups.push({
				matcher: typeof group.matcher === "string" ? group.matcher : undefined,
				hooks: validEntries,
			});
		}
		if (validGroups.length > 0) normalized[key] = validGroups;
	}
	return normalized;
}

export function resolveBundledHookPaths(config: HooksConfig): HooksConfig {
	const resolved: HooksConfig = {};
	for (const [eventName, groups] of Object.entries(config)) {
		if (!groups) continue;
		resolved[eventName] = groups.map((group) => ({
			matcher: group.matcher,
			hooks: group.hooks.map((entry) => ({
				...entry,
				config: {
					...entry.config,
					command: entry.config.command.replaceAll(PI_HOOKS_DIR_PLACEHOLDER, HOOKS_DIR),
				},
			})),
		}));
	}
	return resolved;
}

export function extractHookRunnerOptions(parsed: unknown): HookRunnerOptions {
	if (!isRecord(parsed)) return {};
	const raw = parsed.hookRunner;
	if (!isRecord(raw)) return {};
	const opts: HookRunnerOptions = {
		disableBundledHooks: raw.disableBundledHooks === true,
	};
	if (Array.isArray(raw.disabledHooks)) {
		opts.disabledHooks = raw.disabledHooks.filter((v): v is string => typeof v === "string");
	}
	return opts;
}

export function extractHooksConfig(parsed: unknown, configPath: string): HooksConfig {
	if (!isRecord(parsed)) return {};
	const nestedHooks = parsed.hooks;
	if (isRecord(nestedHooks)) {
		return normalizeHookConfig(nestedHooks);
	}
	if (configPath.endsWith("hooks.json")) {
		return normalizeHookConfig(parsed);
	}
	return {};
}

export function tagEntries(config: HooksConfig, source: HookSource): HooksConfig {
	const out: HooksConfig = {};
	for (const [eventName, groups] of Object.entries(config)) {
		if (!groups) continue;
		out[eventName] = groups.map((group) => ({
			matcher: group.matcher,
			hooks: group.hooks.map((entry) => ({ ...entry, source })),
		}));
	}
	return out;
}

export function basename(commandPath: string): string {
	const trimmed = commandPath.trim().split(/\s+/)[0] ?? "";
	return trimmed.split("/").pop() ?? trimmed;
}

export function applyDisabled(config: HooksConfig, disabled: Set<string>): void {
	if (disabled.size === 0) return;
	for (const groups of Object.values(config)) {
		if (!groups) continue;
		for (const group of groups) {
			for (const entry of group.hooks) {
				if (disabled.has(basename(entry.config.command))) {
					entry.disabled = true;
				}
			}
		}
	}
}

export function filterEnabled(config: HooksConfig): HooksConfig {
	const out: HooksConfig = {};
	for (const [eventName, groups] of Object.entries(config)) {
		if (!groups) continue;
		const filteredGroups = groups
			.map((group) => ({
				matcher: group.matcher,
				hooks: group.hooks.filter((entry) => !entry.disabled),
			}))
			.filter((group) => group.hooks.length > 0);
		if (filteredGroups.length > 0) {
			out[eventName] = filteredGroups;
		}
	}
	return out;
}

export function hasUnsupportedIfPredicate(config: HooksConfig): boolean {
	return Object.values(config)
		.flat()
		.flatMap((g) => g?.hooks ?? [])
		.some((h) => "if" in h.config);
}

export function mergeHooks(base: HooksConfig, user: HooksConfig): void {
	for (const [key, groups] of Object.entries(user)) {
		if (!groups) continue;
		const existing = base[key];
		base[key] = existing ? [...existing, ...groups] : [...groups];
	}
}
