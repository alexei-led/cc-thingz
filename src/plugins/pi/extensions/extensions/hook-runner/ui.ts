/**
 * /hooks interactive command — TUI for inspecting, toggling, and editing
 * project- or global-scope hook configuration.
 */

import type { ExtensionAPI, ExtensionContext } from "@earendil-works/pi-coding-agent";
import { readFileSync } from "node:fs";

import {
	globalHooksConfigPath,
	hooksSummary,
	listAllHookNames,
	loadConfig,
	projectHooksConfigPath,
	rawConfig,
	readProjectHookRunnerOptions,
	writeHooksConfig,
} from "./config.js";
import { isRecord } from "./types.js";
import type { HookSource } from "./types.js";

export function registerHooksCommand(pi: ExtensionAPI): void {
	pi.registerCommand("hooks", {
		description: "Manage hook-runner config (project and global hooks.json)",
		handler: async (_args, ctx) => {
			if (!ctx.hasUI) {
				ctx.ui.notify("Hooks UI is only available in interactive mode.", "warning");
				return;
			}
			loadConfig(ctx.cwd);
			const options = readProjectHookRunnerOptions(ctx.cwd);
			const disableBundled = options.disableBundledHooks === true;
			const choice = await ctx.ui.select("Hook runner", [
				"Show active hooks",
				"Toggle individual hook",
				disableBundled ? "Enable bundled hooks (project)" : "Disable bundled hooks (project)",
				"Edit project hooks (.pi/hooks.json)",
				"Edit global hooks (~/.pi/agent/hooks.json)",
			]);
			if (choice === "Show active hooks") {
				ctx.ui.notify(hooksSummary(rawConfig()), "info");
				return;
			}
			if (choice === "Toggle individual hook") {
				await toggleIndividualHook(ctx);
				return;
			}
			if (choice === "Edit project hooks (.pi/hooks.json)") {
				await editHooksFile(ctx, projectHooksConfigPath(ctx.cwd), "project");
				return;
			}
			if (choice === "Edit global hooks (~/.pi/agent/hooks.json)") {
				await editHooksFile(ctx, globalHooksConfigPath(), "global");
				return;
			}
			if (choice === "Disable bundled hooks (project)" || choice === "Enable bundled hooks (project)") {
				toggleBundledHooks(projectHooksConfigPath(ctx.cwd), choice.startsWith("Disable"));
				loadConfig(ctx.cwd, true);
				ctx.ui.notify(choice.startsWith("Disable") ? "Bundled hooks disabled in .pi/hooks.json" : "Bundled hooks enabled in .pi/hooks.json", "info");
			}
		},
	});
}

async function toggleIndividualHook(ctx: ExtensionContext): Promise<void> {
	const names = listAllHookNames(rawConfig());
	if (names.length === 0) {
		ctx.ui.notify("No hooks to toggle.", "info");
		return;
	}
	const label = (e: { name: string; disabled: boolean; source: HookSource }) => `${e.disabled ? "[ ]" : "[x]"} ${e.name} (${e.source})`;
	const scope = await ctx.ui.select("Write toggle to:", ["Project (.pi/hooks.json)", "Global (~/.pi/agent/hooks.json)"]);
	if (!scope) return;
	const path = scope.startsWith("Project") ? projectHooksConfigPath(ctx.cwd) : globalHooksConfigPath();
	const picked = await ctx.ui.select("Toggle hook:", names.map(label));
	if (!picked) return;
	const idx = names.findIndex((e) => label(e) === picked);
	if (idx < 0) return;
	const target = names[idx];
	const scopeDisabled = readDisabledList(path).includes(target.name);
	const willDisable = !scopeDisabled;
	updateDisabledList(path, target.name, willDisable);
	loadConfig(ctx.cwd, true);
	ctx.ui.notify(`${willDisable ? "Disabled" : "Enabled"} ${target.name} (${scope.startsWith("Project") ? "project" : "global"})`, "info");
}

async function editHooksFile(ctx: ExtensionContext, path: string, scope: HookSource): Promise<void> {
	let initial = "{}\n";
	try {
		initial = readFileSync(path, "utf-8");
	} catch {
		// keep default
	}
	const edited = await ctx.ui.editor(`Edit ${scope} hooks (${path}):`, initial);
	if (!edited || !edited.trim()) return;
	try {
		const parsed = JSON.parse(edited) as unknown;
		if (!isRecord(parsed)) {
			ctx.ui.notify("hooks.json must be a JSON object.", "error");
			return;
		}
		writeHooksConfig(path, parsed);
		loadConfig(ctx.cwd, true);
		ctx.ui.notify(`Updated ${scope} hooks.json`, "info");
	} catch {
		ctx.ui.notify("Invalid JSON. Not saved.", "error");
	}
}

function toggleBundledHooks(path: string, disable: boolean): void {
	let parsed: Record<string, unknown> = {};
	try {
		const raw = readFileSync(path, "utf-8");
		const current = JSON.parse(raw) as unknown;
		if (isRecord(current)) parsed = current;
	} catch {
		// start from empty object
	}
	const hookRunner = isRecord(parsed.hookRunner) ? (parsed.hookRunner as Record<string, unknown>) : {};
	hookRunner.disableBundledHooks = disable;
	parsed.hookRunner = hookRunner;
	writeHooksConfig(path, parsed);
}

function readDisabledList(path: string): string[] {
	try {
		const raw = readFileSync(path, "utf-8");
		const parsed = JSON.parse(raw) as unknown;
		if (!isRecord(parsed)) return [];
		const hookRunner = parsed.hookRunner;
		if (!isRecord(hookRunner)) return [];
		if (!Array.isArray(hookRunner.disabledHooks)) return [];
		return hookRunner.disabledHooks.filter((v): v is string => typeof v === "string");
	} catch {
		return [];
	}
}

function updateDisabledList(path: string, name: string, disable: boolean): void {
	let parsed: Record<string, unknown> = {};
	try {
		const raw = readFileSync(path, "utf-8");
		const current = JSON.parse(raw) as unknown;
		if (isRecord(current)) parsed = current;
	} catch {
		// start from empty object
	}
	const hookRunner = isRecord(parsed.hookRunner) ? (parsed.hookRunner as Record<string, unknown>) : {};
	const current = Array.isArray(hookRunner.disabledHooks) ? hookRunner.disabledHooks.filter((v): v is string => typeof v === "string") : [];
	const next = disable ? [...new Set([...current, name])] : current.filter((n) => n !== name);
	hookRunner.disabledHooks = next;
	parsed.hookRunner = hookRunner;
	writeHooksConfig(path, parsed);
}
