import { beforeEach, describe, expect, it, mock, spyOn } from "bun:test";

const { default: permissionGate } = await import("../../../src/plugins/pi/extensions/extensions/permission-gate.ts");

type Handler = (event: { toolName: string; input: Record<string, unknown> }, ctx: any) => Promise<unknown>;

type HookPayload = {
	hookEventName: string;
	onResult?: (result: Record<string, unknown>) => void;
	stdin?: Record<string, unknown>;
};

function setup() {
	const handlers = new Map<string, Handler>();
	let responder: ((payload: HookPayload) => void) | undefined;

	const pi = {
		on: (event: string, handler: Handler) => handlers.set(event, handler),
		registerCommand: () => {},
		events: {
			emit: (_channel: string, payload: unknown) => {
				const p = payload as HookPayload;
				if (responder) {
					responder(p);
				} else {
					// Default: no hook decision — resolve immediately so invokeSyntheticHook
					// doesn't wait for its timeout before falling through to the UI path.
					p.onResult?.({});
				}
			},
		},
	};

	permissionGate(pi as any);
	return {
		handlers,
		setResponder: (fn: typeof responder) => {
			responder = fn;
		},
	};
}

function makeCtx(hasUI: boolean, selectResult?: string) {
	return {
		hasUI,
		cwd: "/workspace",
		sessionManager: { getSessionId: () => "sess-test" },
		ui: {
			select: mock(async () => selectResult),
			notify: mock(),
		},
	};
}

describe("permission-gate / tool_call", () => {
	beforeEach(() => {
		mock.restore();
	});

	it("allows non-bash tools unconditionally", async () => {
		const { handlers } = setup();
		const handler = handlers.get("tool_call")!;
		expect(await handler({ toolName: "write", input: {} }, makeCtx(false))).toBeUndefined();
		expect(await handler({ toolName: "read", input: {} }, makeCtx(false))).toBeUndefined();
	});

	it("allows non-dangerous bash commands without prompting", async () => {
		const { handlers } = setup();
		const handler = handlers.get("tool_call")!;
		const ctx = makeCtx(true);
		const result = await handler({ toolName: "bash", input: { command: "ls -la /tmp" } }, ctx);
		expect(result).toBeUndefined();
		expect(ctx.ui.select).not.toHaveBeenCalled();
	});

	it.each(["echo 'sudo is required'", "printf '%s' 'rm -rf /tmp'", "echo 'chmod 777'"])("allows literal display arguments headlessly: %s", async (command) => {
		const { handlers, setResponder } = setup();
		const responder = mock();
		setResponder(responder);
		const result = await handlers.get("tool_call")!({ toolName: "bash", input: { command } }, makeCtx(false));
		expect(result).toBeUndefined();
		expect(responder).not.toHaveBeenCalled();
	});

	it.each([
		"agtermctl tree --json",
		"agtermctl session new --name worker --command 'sudo whoami'",
		"agtermctl session type --target abc --text 'sudo whoami'",
		"agtermctl session text --target abc",
		"herdr pane split --current --direction right --no-focus",
		"herdr pane read 123 --source recent-unwrapped",
		"herdr agent prompt worker 'Review sudo usage'",
		"herdr pane run 123 'sudo whoami'",
	])("allows literal terminal control commands by default: %s", async (command) => {
		const { handlers } = setup();
		const result = await handlers.get("tool_call")!({ toolName: "bash", input: { command } }, makeCtx(false));
		expect(result).toBeUndefined();
	});

	it.each(["agtermctl tree; sudo whoami", "herdr pane read 123 && sudo whoami"])("does not exempt separate shell commands: %s", async (command) => {
		const { handlers } = setup();
		const result = await handlers.get("tool_call")!({ toolName: "bash", input: { command } }, makeCtx(false));
		expect(result).toMatchObject({ block: true });
	});

	it.each(["rm -f /tmp/file", "rm -- -rf", "rm --recursive-file", "rm -rf-file"])(
		"does not confuse operand tokens with recursive flags: %s",
		async (command) => {
			const { handlers } = setup();
			const handler = handlers.get("tool_call")!;
			const ctx = makeCtx(true);
			expect(await handler({ toolName: "bash", input: { command } }, ctx)).toBeUndefined();
			expect(ctx.ui.select).not.toHaveBeenCalled();
		},
	);

	it.each([42, null, undefined, "", " \t\n"])("blocks invalid bash command input: %j", async (command) => {
		const { handlers, setResponder } = setup();
		const responder = mock();
		setResponder(responder);
		const handler = handlers.get("tool_call")!;
		const ctx = makeCtx(true);
		const result = await handler({ toolName: "bash", input: { command } }, ctx);
		expect(responder).not.toHaveBeenCalled();
		expect(ctx.ui.select).not.toHaveBeenCalled();
		expect(result).toEqual({
			block: true,
			reason: "Invalid bash command input",
		});
	});

	it("fails closed when PermissionRequest hook times out", async () => {
		const { handlers, setResponder } = setup();
		const handler = handlers.get("tool_call")!;
		setResponder((_payload) => {
			// Intentionally do not call onResult, forcing timeout.
		});

		const schedule = globalThis.setTimeout;
		const immediate = Object.assign((callback: (...args: unknown[]) => void, _delay?: number, ...args: unknown[]) => schedule(callback, 0, ...args), {
			__promisify__: schedule.__promisify__,
		});
		const timer = spyOn(globalThis, "setTimeout").mockImplementation(immediate as typeof setTimeout);
		try {
			const result = await handler({ toolName: "bash", input: { command: "sudo rm -rf /tmp" } }, makeCtx(false));
			expect(timer).toHaveBeenCalledWith(expect.any(Function), 2000);
			expect(result).toMatchObject({
				block: true,
				reason: "Permission request hook timed out.",
			});
		} finally {
			timer.mockRestore();
		}
	});

	it("honors hook allow with updated command", async () => {
		const { handlers, setResponder } = setup();
		const handler = handlers.get("tool_call")!;
		setResponder((payload) => {
			if (payload.hookEventName !== "PermissionRequest") {
				payload.onResult?.({});
				return;
			}
			payload.onResult?.({
				behavior: "allow",
				updatedInput: { command: "echo sanitized" },
			});
		});

		const event = { toolName: "bash", input: { command: "sudo whoami" } };
		const result = await handler(event, makeCtx(true, "No"));
		expect(result).toBeUndefined();
		expect(event.input.command).toBe("echo sanitized");
	});

	it("blocks a hook update that still matches a dangerous command pattern", async () => {
		const { handlers, setResponder } = setup();
		const handler = handlers.get("tool_call")!;
		setResponder((payload) => {
			if (payload.hookEventName === "PermissionRequest") {
				payload.onResult?.({
					behavior: "allow",
					updatedInput: { command: "rm -fr /tmp" },
				});
			} else {
				payload.onResult?.({});
			}
		});

		const result = await handler({ toolName: "bash", input: { command: "sudo whoami" } }, makeCtx(true));
		expect(result).toEqual({
			block: true,
			reason: "PermissionRequest hook returned an unsafe command patch",
		});
	});

	it("blocks when hook allow returns updatedInput without a command string", async () => {
		const { handlers, setResponder } = setup();
		const handler = handlers.get("tool_call")!;
		setResponder((payload) => {
			if (payload.hookEventName !== "PermissionRequest") {
				payload.onResult?.({});
				return;
			}
			payload.onResult?.({
				behavior: "allow",
				updatedInput: { notACommand: 42 },
			});
		});

		const result = await handler({ toolName: "bash", input: { command: "sudo whoami" } }, makeCtx(true));
		expect(result).toEqual({
			block: true,
			reason: "PermissionRequest hook returned invalid command patch",
		});
	});

	it("honors hook deny before UI prompt", async () => {
		const { handlers, setResponder } = setup();
		const handler = handlers.get("tool_call")!;
		setResponder((payload) => {
			if (payload.hookEventName === "PermissionRequest") {
				payload.onResult?.({ behavior: "deny", message: "blocked by policy" });
				return;
			}
			payload.onResult?.({ retry: false });
		});

		const ctx = makeCtx(true, "Yes");
		const result = await handler({ toolName: "bash", input: { command: "sudo whoami" } }, ctx);
		expect(result).toEqual({ block: true, reason: "blocked by policy" });
		expect(ctx.ui.select).not.toHaveBeenCalled();
	});

	it.each([
		"sudo rm -rf /var",
		"rm -rf /tmp",
		"rm -fr /tmp",
		"rm -f -r /tmp",
		"rm -R /tmp",
		"rm --force --recursive /tmp",
		"rm --recursive /tmp",
		"sudo whoami",
		"chmod 777 /tmp",
		"cd /tmp && sudo whoami",
		"printf ok | sudo tee /tmp/log",
		"/usr/bin/sudo whoami",
		"env FOO=bar sudo whoami",
		"env -i sudo whoami",
		"command -- sudo whoami",
		"echo ${#PATH}; sudo whoami",
		"a{#b; sudo whoami",
		"env -S 'sudo whoami'",
		"exec -a example sudo whoami",
		"exec -c sudo whoami",
		"exec -a example -c sudo whoami",
		"stdbuf -oL sudo whoami",
		"ionice -c 2 sudo whoami",
		"echo ${#files[@]}; rm -rf build",
		"time sudo whoami",
		"time rm -rf build",
		"nohup sudo whoami",
		"timeout 5 sudo whoami",
		"nice rm -rf build",
		"find . | xargs rm -rf",
		"find . -name x -exec rm -rf {} +",
		"< /dev/null sudo whoami",
		"sudo>/dev/null whoami",
		"sudo</dev/null whoami",
		"sudo 2>/dev/null whoami",
		"/usr/bin/sudo>/dev/null whoami",
		"2>/dev/null sudo whoami",
		"chmod 1777 /tmp/example",
		"chmod 2777 /tmp/example",
		"chmod 4777 /tmp/example",
		"chmod 7777 /tmp/example",
		"echo $(sudo whoami)",
		'echo "$(sudo whoami)"',
		"cat <<EOF\n$(sudo whoami)\nEOF",
		"python - <<'PY'\ntext = 'sudo'\nPY\nsudo whoami",
	])("blocks %s without a UI", async (command) => {
		const { handlers } = setup();
		const handler = handlers.get("tool_call")!;
		const result = await handler({ toolName: "bash", input: { command } }, makeCtx(false));
		expect(result).toMatchObject({
			block: true,
			reason: expect.stringContaining("no UI"),
		});
	});

	it.each([
		"python -c 'text = \"sudo rm -rf /example\"'",
		"node -e 'console.log(\"sudo\")'",
		"uv run --no-project python - <<PY\ntext = 'sudo'\nprint(text)\nPY",
		"printf '%s' 'sudo rm -rf /example'",
		"rg -F 'sudo' README.md",
		"cd /tmp && uv run --no-project python - <<'PY'\ntext = 'sudo'\nPY\nmake check",
	])("does not warn on developer source and data: %s", async (command) => {
		const { handlers } = setup();
		expect(await handlers.get("tool_call")!({ toolName: "bash", input: { command } }, makeCtx(false))).toBeUndefined();
	});
	it("keeps hook vetoes for source-text false positives", async () => {
		const { handlers, setResponder } = setup();
		setResponder((payload) => payload.onResult?.(payload.hookEventName === "PermissionRequest" ? { behavior: "deny", reason: "hook policy" } : {}));
		expect(await handlers.get("tool_call")!({ toolName: "bash", input: { command: "python -c 'print(\"sudo\")'" } }, makeCtx(false))).toEqual({
			block: true,
			reason: "hook policy",
		});
	});

	it("allows dangerous command when UI prompt answered Yes", async () => {
		const { handlers } = setup();
		const handler = handlers.get("tool_call")!;
		const result = await handler({ toolName: "bash", input: { command: "sudo whoami" } }, makeCtx(true, "Yes"));
		expect(result).toBeUndefined();
	});

	it("blocks dangerous command when UI prompt answered No", async () => {
		const { handlers } = setup();
		const handler = handlers.get("tool_call")!;
		const result = await handler({ toolName: "bash", input: { command: "sudo whoami" } }, makeCtx(true, "No"));
		expect(result).toMatchObject({ block: true, reason: "Blocked by user" });
	});

	it("appends retry hint when PermissionDenied hook signals retry", async () => {
		const { handlers, setResponder } = setup();
		const handler = handlers.get("tool_call")!;
		setResponder((payload) => {
			if (payload.hookEventName === "PermissionDenied") {
				payload.onResult?.({ retry: true });
			} else {
				// PermissionRequest: no decision, fall through to UI
				payload.onResult?.({});
			}
		});

		const result = await handler({ toolName: "bash", input: { command: "sudo whoami" } }, makeCtx(true, "No"));
		expect(result).toMatchObject({
			block: true,
			reason: expect.stringContaining("retry is allowed"),
		});
	});
});
