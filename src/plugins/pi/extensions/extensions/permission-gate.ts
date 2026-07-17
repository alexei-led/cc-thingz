/**
 * Permission Gate Extension
 *
 * Prompts for confirmation before running potentially dangerous bash commands.
 * Patterns checked: rm -rf, sudo, chmod/chown 777
 */

import type {
  ExtensionAPI,
  ExtensionContext,
} from "@earendil-works/pi-coding-agent";
import {
  invokeSyntheticHook,
  type SyntheticHookInvocationResult,
  toCcToolName,
} from "./shared/hook-bridge.js";

export default function (pi: ExtensionAPI) {
  const dangerousPatterns = [
    /\brm\s+(-rf?|--recursive)/i,
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

    const isDangerous = dangerousPatterns.some((p) => p.test(commandRaw));
    if (!isDangerous) {
      return undefined;
    }

    const requestHook = await invokeHook(ctx, "PermissionRequest", {
      command: commandRaw,
    });
    if (requestHook.behavior === "deny" || requestHook.blocked) {
      const reason =
        requestHook.reason ||
        requestHook.message ||
        "Permission denied by hook";
      await invokeHook(
        ctx,
        "PermissionDenied",
        { command: commandRaw },
        reason,
      );
      return { block: true, reason };
    }
    if (requestHook.behavior === "allow") {
      if (
        requestHook.updatedInput &&
        typeof requestHook.updatedInput.command === "string"
      ) {
        const updatedCommand = requestHook.updatedInput.command;
        if (dangerousPatterns.some((pattern) => pattern.test(updatedCommand))) {
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

    if (!ctx.hasUI) {
      const reason = "Dangerous command blocked (no UI for confirmation)";
      const denied = await invokeHook(
        ctx,
        "PermissionDenied",
        { command: commandRaw },
        reason,
      );
      return {
        block: true,
        reason: denied.retry
          ? `${reason} (hook signaled retry is allowed)`
          : reason,
      };
    }

    const choice = await ctx.ui.select(
      `⚠️ Dangerous command:\n\n  ${commandRaw}\n\nAllow?`,
      ["Yes", "No"],
    );
    if (choice === "Yes") {
      return undefined;
    }

    const reason = "Blocked by user";
    const denied = await invokeHook(
      ctx,
      "PermissionDenied",
      { command: commandRaw },
      reason,
    );
    return {
      block: true,
      reason: denied.retry
        ? `${reason} (hook signaled retry is allowed)`
        : reason,
    };
  });
}
