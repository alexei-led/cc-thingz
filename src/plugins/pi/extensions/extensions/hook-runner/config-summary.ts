/**
 * Render helpers for the `/hooks` slash command.
 */

import { basename } from "./config-parse.js";
import type { HooksConfig, HookSource } from "./types.js";

export function hooksSummary(config: HooksConfig): string {
	const lines: string[] = [];
	const events = Object.keys(config).sort();
	for (const eventName of events) {
		const groups = config[eventName];
		if (!groups || groups.length === 0) continue;
		lines.push(`${eventName}:`);
		for (const group of groups) {
			const matcher = group.matcher ? `[${group.matcher}]` : "[*]";
			for (const entry of group.hooks) {
				const status = entry.disabled ? " (disabled)" : "";
				const flags = entry.config.async ? " async" : "";
				lines.push(`  ${matcher} ${basename(entry.config.command)} (${entry.source})${flags}${status}`);
			}
		}
	}
	if (lines.length === 0) return "No hooks configured.";
	return lines.join("\n");
}

export interface HookNameEntry {
	name: string;
	disabled: boolean;
	source: HookSource;
}

export function listAllHookNames(config: HooksConfig): HookNameEntry[] {
	const seen = new Map<string, HookNameEntry>();
	for (const groups of Object.values(config)) {
		if (!groups) continue;
		for (const group of groups) {
			for (const entry of group.hooks) {
				const name = basename(entry.config.command);
				if (!name) continue;
				const existing = seen.get(name);
				if (!existing) {
					seen.set(name, { name, disabled: entry.disabled, source: entry.source });
				} else if (entry.disabled) {
					existing.disabled = true;
				}
			}
		}
	}
	return [...seen.values()].sort((a, b) => a.name.localeCompare(b.name));
}
