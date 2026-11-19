/**
 * Permission Gate Extension
 *
 * Applies optional literal Bash permission rules and warns on dangerous commands.
 * Provides /permissions; this is an approval aid, not a sandbox.
 */

import type { ExtensionAPI, ExtensionContext } from "@earendil-works/pi-coding-agent";
import { loadPolicy, matchesRule, parseLiteralCommand, parseOutputPipeline, type Policy } from "./shared/permission-rules.js";
import { invokeSyntheticHook, type SyntheticHookInvocationResult, toCcToolName } from "./shared/hook-bridge.js";

export default function (pi: ExtensionAPI) {
	let policy: Policy = { allow: [], deny: [] };
	let userPolicy: Policy = policy;
	pi.on("session_start", async (_event, ctx) => {
		userPolicy = loadPolicy(ctx.cwd, false);
		policy = ctx.isProjectTrusted() ? loadPolicy(ctx.cwd, true) : userPolicy;
		if (ctx.hasUI && (policy.error || policy.warning)) ctx.ui.notify(policy.error || policy.warning || "", policy.error ? "error" : "warning");
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
		const deny = async (reason: string) => {
			const denied = await invokeHook(ctx, "PermissionDenied", { command: commandRaw }, reason);
			return { block: true, reason: denied.retry ? `${reason} (hook signaled retry is allowed)` : reason };
		};
		if (effective.error) return deny(effective.error);
		const hasRules = effective.allow.length > 0 || effective.deny.length > 0;
		const pipeline = hasRules ? parseOutputPipeline(commandRaw) : undefined;
		const words = hasRules ? (parseLiteralCommand(commandRaw) ?? pipeline?.words) : undefined;
		const ruleMatch = words && effective.allow.find((rule) => matchesRule(rule, words));
		const unrecognized = hasRules && (!words || (!!pipeline && !ruleMatch));
		if (words && effective.deny.some((rule) => matchesRule(rule, words, true) || (!!pipeline && matchesRule(rule, pipeline.filter, true))))
			return deny("Blocked by user permission rule");
		const allowed = ruleMatch && (ctx.hasUI || ruleMatch.headless);
		const isDangerous = dangerousPatterns.some((p) => p.test(commandRaw));
		const restrictedExecutable = words && effective.allow.some((rule) => rule.words[0] === words[0]);
		if (!isDangerous && !restrictedExecutable && !unrecognized) return undefined;

		const requestHook = await invokeHook(ctx, "PermissionRequest", {
			command: commandRaw,
		});
		if (requestHook.behavior === "deny" || requestHook.blocked) {
			const reason = requestHook.reason || requestHook.message || "Permission denied by hook";
			return deny(reason);
		}
		if (unrecognized && effective.deny.length > 0) return deny("Unrecognized shell syntax cannot be checked against deny rules");
		if (requestHook.behavior === "allow") {
			if (requestHook.updatedInput && typeof requestHook.updatedInput.command === "string") {
				const updatedCommand = requestHook.updatedInput.command;
				const updatedWords = hasRules ? parseLiteralCommand(updatedCommand) : undefined;
				if (
					(hasRules && !updatedWords) ||
					(updatedWords && effective.deny.some((rule) => matchesRule(rule, updatedWords, true))) ||
					dangerousPatterns.some((pattern) => pattern.test(updatedCommand))
				) {
					return deny("PermissionRequest hook returned an unsafe command patch");
				}
				event.input.command = updatedCommand;
				return undefined;
			}
			if (requestHook.updatedInput) {
				return deny("PermissionRequest hook returned invalid command patch");
			}
			return undefined;
		}

		if (allowed) return undefined;

		if (!ctx.hasUI)
			return deny(unrecognized ? "Unrecognized shell syntax blocked (no UI for confirmation)" : "Dangerous command blocked (no UI for confirmation)");

		const label = unrecognized ? "Unrecognized shell syntax" : "Dangerous command";
		const choice = await ctx.ui.select(`⚠️ ${label}:\n\n  ${commandRaw}\n\nAllow?`, ["Yes", "No"]);
		if (choice === "Yes") {
			return undefined;
		}

		return deny("Blocked by user");
	});
}
