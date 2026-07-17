import { describe, expect, it } from "bun:test";
import type { ExtensionAPI, ExtensionContext } from "@earendil-works/pi-coding-agent";

import {
	HOOK_RUNNER_INVOKE_CHANNEL,
	invokeSyntheticHook,
	SYNTHETIC_HOOK_DEFAULT_TIMEOUT_SEC,
	SYNTHETIC_HOOK_OUTER_WAIT_MARGIN_MS,
	toCcToolName,
} from "../../../src/plugins/pi/extensions/extensions/shared/hook-bridge.ts";

// ---------------------------------------------------------------------------
// toCcToolName — table-driven
// ---------------------------------------------------------------------------

describe("toCcToolName", () => {
	it.each([
		["bash", "Bash"],
		["write", "Write"],
		["edit", "Edit"],
		["multiedit", "MultiEdit"],
		["read", "Read"],
		["grep", "Grep"],
		["find", "Glob"],
		["ls", "Ls"],
		["subagent", "Agent"],
		["ask_user_question", "AskUserQuestion"],
		["exit_plan_mode", "ExitPlanMode"],
	])("maps %p to %p", (input, expected) => {
		expect(toCcToolName(input)).toBe(expected);
	});

	it("capitalises unregistered single-word lowercase names", () => {
		expect(toCcToolName("finder")).toBe("Finder");
	});

	it("returns underscored names as-is (no silent inference)", () => {
		expect(toCcToolName("read_url")).toBe("read_url");
	});

	it("returns already-cased names as-is", () => {
		expect(toCcToolName("CustomTool")).toBe("CustomTool");
	});
});

// ---------------------------------------------------------------------------
// invokeSyntheticHook — outer-wait floor enforcement
// ---------------------------------------------------------------------------

function makePi(captureEmit: (channel: string, payload: unknown) => void): ExtensionAPI {
	return {
		events: {
			emit: (channel: string, payload: unknown) => captureEmit(channel, payload),
			on: () => {},
		},
		sendUserMessage: () => {},
	} as unknown as ExtensionAPI;
}

function makeCtx(): ExtensionContext {
	return {
		sessionManager: { getSessionId: () => "sess-1" },
		cwd: "/tmp/work",
		isIdle: () => true,
		hasUI: false,
		ui: { notify: () => {}, select: async () => undefined, editor: async () => "" },
	} as unknown as ExtensionContext;
}

describe("invokeSyntheticHook", () => {
	it("derives outer wait from timeoutSec + margin when timeoutMs omitted", async () => {
		let observedTimeoutSec: number | undefined;
		const pi = makePi((_channel, raw) => {
			const payload = raw as { timeoutSec?: number; onResult?: (r: unknown) => void };
			observedTimeoutSec = payload.timeoutSec;
			payload.onResult?.({ blocked: false });
		});
		const result = await invokeSyntheticHook(pi, makeCtx(), {
			hookEventName: "PreToolUse",
			stdin: { session_id: "sess-1", cwd: "/tmp/work" },
		});
		expect(result).toEqual({ blocked: false });
		expect(observedTimeoutSec).toBe(SYNTHETIC_HOOK_DEFAULT_TIMEOUT_SEC);
	});

	it("honors explicit short timeoutMs verbatim by default (interactive flow)", async () => {
		const pi = makePi(() => {
			// Never call onResult — force outer-wait fire.
		});
		const started = Date.now();
		const result = await invokeSyntheticHook(pi, makeCtx(), {
			hookEventName: "PermissionRequest",
			stdin: { session_id: "sess-1", cwd: "/tmp/work" },
			timeoutMs: 100,
			timeoutResult: { blocked: true, reason: "test timeout" },
		});
		const elapsed = Date.now() - started;
		expect(result).toEqual({ blocked: true, reason: "test timeout" });
		expect(elapsed).toBeLessThan(SYNTHETIC_HOOK_OUTER_WAIT_MARGIN_MS);
		expect(elapsed).toBeGreaterThanOrEqual(95);
	});

	it("clamps explicit short timeoutMs up to floor when enforceFloor is true", async () => {
		let observedOnResult: ((r: unknown) => void) | undefined;
		const pi = makePi((_channel, raw) => {
			const payload = raw as { onResult?: (r: unknown) => void };
			observedOnResult = payload.onResult;
		});
		const promise = invokeSyntheticHook(pi, makeCtx(), {
			hookEventName: "PreToolUse",
			stdin: { session_id: "sess-1", cwd: "/tmp/work" },
			timeoutSec: 1,
			timeoutMs: 100,
			enforceFloor: true,
		});
		// If the floor were ignored, the outer wait would fire at ~100ms and we'd
		// settle to {} (no timeoutResult set). Instead we expect the resolve to
		// only fire when we deliver a hook-runner reply, proving the floor held.
		await new Promise((resolve) => setTimeout(resolve, 200));
		expect(observedOnResult).toBeDefined();
		observedOnResult!({ blocked: false, reason: "via floor path" });
		const result = await promise;
		expect(result).toEqual({ blocked: false, reason: "via floor path" });
	});

	it("emits onto the documented channel", async () => {
		let observedChannel = "";
		const pi = makePi((channel, raw) => {
			observedChannel = channel;
			const payload = raw as { onResult?: (r: unknown) => void };
			payload.onResult?.({ blocked: false });
		});
		await invokeSyntheticHook(pi, makeCtx(), {
			hookEventName: "PreToolUse",
			stdin: { session_id: "sess-1", cwd: "/tmp/work" },
		});
		expect(observedChannel).toBe(HOOK_RUNNER_INVOKE_CHANNEL);
	});

	it("returns empty result when session_id missing", async () => {
		const pi = makePi(() => {});
		const ctx = { sessionManager: { getSessionId: () => undefined }, cwd: "/tmp/work" } as unknown as ExtensionContext;
		const result = await invokeSyntheticHook(pi, ctx, {
			hookEventName: "PreToolUse",
			stdin: {},
		});
		expect(result).toEqual({});
	});

	it("returns empty result immediately when emit throws (event bus torn down)", async () => {
		const pi = {
			events: {
				emit: () => {
					throw new Error("session ended");
				},
				on: () => {},
			},
			sendUserMessage: () => {},
		} as unknown as ExtensionAPI;
		const started = Date.now();
		const result = await invokeSyntheticHook(pi, makeCtx(), {
			hookEventName: "PreToolUse",
			stdin: { session_id: "sess-1", cwd: "/tmp/work" },
			timeoutMs: 5000,
			timeoutResult: { blocked: true, reason: "should not see this" },
		});
		const elapsed = Date.now() - started;
		// Emit threw → done({}) fires synchronously, no waiting on outer timer.
		expect(result).toEqual({});
		expect(elapsed).toBeLessThan(500);
	});
});
