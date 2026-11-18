/**
 * Permission Gate Extension
 *
 * Prompts for confirmation before running potentially dangerous bash commands.
 * Warning heuristic, not a shell parser or sandbox.
 * Patterns checked: recursive rm flags, sudo, chmod/chown 777.
 */

import type { ExtensionAPI, ExtensionContext } from "@earendil-works/pi-coding-agent";
import { loadPolicy, matchesRule, parseLiteralCommand, type Policy } from "./shared/permission-rules.js";
import { invokeSyntheticHook, type SyntheticHookInvocationResult, toCcToolName } from "./shared/hook-bridge.js";

export default function (pi: ExtensionAPI) {
	let policy: Policy = { allow: [], deny: [] };
	let userPolicy: Policy = policy;
	pi.on("session_start", async (_event, ctx) => {
		userPolicy = loadPolicy(ctx.cwd, false);
		policy = ctx.isProjectTrusted() ? loadPolicy(ctx.cwd, true) : userPolicy;
		if (ctx.hasUI && policy.warning) ctx.ui.notify(policy.warning, "warning");
		if (ctx.hasUI && policy.allow.some((rule) => rule.source === "project"))
			ctx.ui.notify("Project permission rules are active. Use /permissions to inspect them.", "warning");
	});
	pi.registerCommand("permissions", {
		description: "Show effective permission-gate rules",
		handler: async (_args, ctx) => {
			const effective = ctx.isProjectTrusted() ? policy : userPolicy;
			const lines = [
				...(effective.error ? [effective.error] : []),
				...(effective.warning ? [effective.warning] : []),
				...effective.deny.map((rule) => `deny [${rule.source}]: ${rule.match}`),
				...effective.allow.map((rule) => `allow [${rule.source}${rule.headless ? ", headless" : ""}]: ${rule.match}`),
			];
			ctx.ui.notify(lines.join("\n") || "No permission-gate rules.", "info");
		},
	});
	const dangerousPatterns = [
		/\brm\s+(?:(?:-[a-zA-Z]+|--[a-z]+(?:-[a-z]+)*)\s+)*(?:-[a-zA-Z]*[rR][a-zA-Z]*|--recursive)(?=\s|$)/,
		/\bsudo\b/i,
		/\b(chmod|chown)\b.*777/i,
	];

	async function invokeHook(
		ctx: ExtensionContext,
		hookEventName: "PermissionRequest" | "PermissionDenied",
		toolInput: Record<string, unknown>,
		reason?: string,
	): Promise<SyntheticHookInvocationResult> {
		const sessionId = ctx.sessionManager?.getSessionId?.();
		const cwd = ctx.cwd;
		if (typeof sessionId !== "string" || typeof cwd !== "string") {
			return {};
		}
		const ccToolName = toCcToolName("bash");
		const stdin: Record<string, unknown> = {
			session_id: sessionId,
			cwd,
			hook_event_name: hookEventName,
			tool_name: ccToolName,
			tool_input: toolInput,
		};
		if (reason) stdin.reason = reason;
		return await invokeSyntheticHook(pi, ctx, {
			hookEventName,
			ccToolName,
			stdin,
			timeoutMs: 2000,
			timeoutResult:
				hookEventName === "PermissionRequest"
					? {
							blocked: true,
							behavior: "deny",
							reason: "Permission request hook timed out.",
						}
					: {},
		});
	}

	pi.on("tool_call", async (event, ctx) => {
		if (event.toolName !== "bash") return undefined;

		const commandRaw = event.input.command;
		if (typeof commandRaw !== "string" || commandRaw.trim() === "") {
			return { block: true, reason: "Invalid bash command input" };
		}

		const effective = ctx.isProjectTrusted?.() ? policy : userPolicy;
		if (effective.error) return { block: true, reason: effective.error };
		const hasRules = effective.allow.length > 0 || effective.deny.length > 0;
		const words = hasRules ? parseLiteralCommand(commandRaw) : undefined;
		if (hasRules && !words) {
			if (effective.deny.length > 0) return { block: true, reason: "Unrecognized shell syntax cannot be checked against deny rules" };
			if (!ctx.hasUI) return { block: true, reason: "Unrecognized shell syntax blocked (no UI for confirmation)" };
			const choice = await ctx.ui.select(`⚠️ Unrecognized shell syntax:\n\n  ${commandRaw}\n\nAllow?`, ["Yes", "No"]);
			return choice === "Yes" ? undefined : { block: true, reason: "Blocked by user" };
		}
		if (words && effective.deny.some((rule) => matchesRule(rule, words))) return { block: true, reason: "Blocked by user permission rule" };
		const allowed = words && effective.allow.find((rule) => matchesRule(rule, words) && (ctx.hasUI || rule.headless));
		const isDangerous = dangerousPatterns.some((p) => p.test(commandRaw));
		const restrictedExecutable = words && effective.allow.some((rule) => rule.words[0] === words[0]);
		if (!isDangerous && !restrictedExecutable) return undefined;

		const requestHook = await invokeHook(ctx, "PermissionRequest", {
			command: commandRaw,
		});
		if (requestHook.behavior === "deny" || requestHook.blocked) {
			const reason = requestHook.reason || requestHook.message || "Permission denied by hook";
			await invokeHook(ctx, "PermissionDenied", { command: commandRaw }, reason);
			return { block: true, reason };
		}
		if (requestHook.behavior === "allow") {
			if (requestHook.updatedInput && typeof requestHook.updatedInput.command === "string") {
				const updatedCommand = requestHook.updatedInput.command;
				const updatedWords = hasRules ? parseLiteralCommand(updatedCommand) : undefined;
				if (
					(hasRules && !updatedWords) ||
					(updatedWords && effective.deny.some((rule) => matchesRule(rule, updatedWords))) ||
					dangerousPatterns.some((pattern) => pattern.test(updatedCommand))
				) {
					return {
						block: true,
						reason: "PermissionRequest hook returned an unsafe command patch",
					};
				}
				event.input.command = updatedCommand;
				return undefined;
			}
			if (requestHook.updatedInput) {
				return {
					block: true,
					reason: "PermissionRequest hook returned invalid command patch",
				};
			}
			return undefined;
		}

		if (allowed) return undefined;

		if (!ctx.hasUI) {
			const reason = "Dangerous command blocked (no UI for confirmation)";
			const denied = await invokeHook(ctx, "PermissionDenied", { command: commandRaw }, reason);
			return {
				block: true,
				reason: denied.retry ? `${reason} (hook signaled retry is allowed)` : reason,
			};
		}

		const choice = await ctx.ui.select(`⚠️ Dangerous command:\n\n  ${commandRaw}\n\nAllow?`, ["Yes", "No"]);
		if (choice === "Yes") {
			return undefined;
		}

		const reason = "Blocked by user";
		const denied = await invokeHook(ctx, "PermissionDenied", { command: commandRaw }, reason);
		return {
			block: true,
			reason: denied.retry ? `${reason} (hook signaled retry is allowed)` : reason,
		};
	});
}
