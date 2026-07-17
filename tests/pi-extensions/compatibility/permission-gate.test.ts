import { beforeEach, describe, expect, it, mock } from "bun:test";

mock.module("@earendil-works/pi-coding-agent", () => ({}));

const { default: permissionGate } =
  await import("../../../src/plugins/pi/extensions/extensions/permission-gate.ts");

type Handler = (
  event: { toolName: string; input: Record<string, unknown> },
  ctx: any,
) => Promise<unknown>;

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
    expect(
      await handler({ toolName: "write", input: {} }, makeCtx(false)),
    ).toBeUndefined();
    expect(
      await handler({ toolName: "read", input: {} }, makeCtx(false)),
    ).toBeUndefined();
  });

  it("allows non-dangerous bash commands without prompting", async () => {
    const { handlers } = setup();
    const handler = handlers.get("tool_call")!;
    const ctx = makeCtx(true);
    const result = await handler(
      { toolName: "bash", input: { command: "ls -la /tmp" } },
      ctx,
    );
    expect(result).toBeUndefined();
    expect(ctx.ui.select).not.toHaveBeenCalled();
  });

  it("blocks invalid bash command input", async () => {
    const { handlers } = setup();
    const handler = handlers.get("tool_call")!;
    const result = await handler(
      { toolName: "bash", input: { command: 42 } },
      makeCtx(false),
    );
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

    const started = Date.now();
    const result = await handler(
      { toolName: "bash", input: { command: "sudo rm -rf /tmp" } },
      makeCtx(false),
    );
    expect(Date.now() - started).toBeGreaterThanOrEqual(1900);
    expect(result).toMatchObject({
      block: true,
      reason: "Permission request hook timed out.",
    });
  });

  it("honors hook allow with updated command", async () => {
    const { handlers, setResponder } = setup();
    const handler = handlers.get("tool_call")!;
    setResponder((payload) => {
      if (payload.hookEventName !== "PermissionRequest") return;
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
          updatedInput: { command: "sudo rm -rf /tmp" },
        });
      }
    });

    const result = await handler(
      { toolName: "bash", input: { command: "sudo whoami" } },
      makeCtx(true),
    );
    expect(result).toEqual({
      block: true,
      reason: "PermissionRequest hook returned an unsafe command patch",
    });
  });

  it("blocks when hook allow returns updatedInput without a command string", async () => {
    const { handlers, setResponder } = setup();
    const handler = handlers.get("tool_call")!;
    setResponder((payload) => {
      if (payload.hookEventName !== "PermissionRequest") return;
      payload.onResult?.({
        behavior: "allow",
        updatedInput: { notACommand: 42 },
      });
    });

    const result = await handler(
      { toolName: "bash", input: { command: "sudo whoami" } },
      makeCtx(true),
    );
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
    const result = await handler(
      { toolName: "bash", input: { command: "sudo whoami" } },
      ctx,
    );
    expect(result).toEqual({ block: true, reason: "blocked by policy" });
    expect(ctx.ui.select).not.toHaveBeenCalled();
  });

  it("blocks dangerous command with no UI and no hook", async () => {
    const { handlers } = setup();
    const handler = handlers.get("tool_call")!;
    const result = await handler(
      { toolName: "bash", input: { command: "sudo rm -rf /var" } },
      makeCtx(false),
    );
    expect(result).toMatchObject({
      block: true,
      reason: expect.stringContaining("no UI"),
    });
  });

  it.each(["rm -rf /tmp", "sudo whoami", "chmod 777 /tmp"])(
    "blocks %s without a UI",
    async (command) => {
      const { handlers } = setup();
      const handler = handlers.get("tool_call")!;
      const result = await handler(
        { toolName: "bash", input: { command } },
        makeCtx(false),
      );
      expect(result).toMatchObject({
        block: true,
        reason: expect.stringContaining("no UI"),
      });
    },
  );

  it("allows dangerous command when UI prompt answered Yes", async () => {
    const { handlers } = setup();
    const handler = handlers.get("tool_call")!;
    const result = await handler(
      { toolName: "bash", input: { command: "sudo whoami" } },
      makeCtx(true, "Yes"),
    );
    expect(result).toBeUndefined();
  });

  it("blocks dangerous command when UI prompt answered No", async () => {
    const { handlers } = setup();
    const handler = handlers.get("tool_call")!;
    const result = await handler(
      { toolName: "bash", input: { command: "sudo whoami" } },
      makeCtx(true, "No"),
    );
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

    const result = await handler(
      { toolName: "bash", input: { command: "sudo whoami" } },
      makeCtx(true, "No"),
    );
    expect(result).toMatchObject({
      block: true,
      reason: expect.stringContaining("retry is allowed"),
    });
  });
});
