import { describe, expect, it } from "bun:test";
import { mock } from "bun:test";

// typebox and pi-ai are Pi peer deps — mock before importing, following the
// ask-user-question.test.ts convention.
mock.module("typebox", () => ({
  Type: {
    Object: (s: unknown) => s,
    String: () => ({}),
    Number: () => ({}),
    Optional: (s: unknown) => s,
  },
}));
mock.module("@earendil-works/pi-ai", () => ({
  StringEnum: (values: readonly string[]) => ({ enum: values }),
}));
mock.module("@earendil-works/pi-coding-agent", () => ({}));
mock.module("@earendil-works/pi-tui", () => ({
  matchesKey: (data: string, key: string) => data === key,
  Text: class {
    constructor(public text: string) {}
  },
  truncateToWidth: (value: string, width: number) => value.slice(0, width),
}));

const { default: todoExtension } =
  await import("../../src/plugins/pi/extensions/extensions/todo.ts");

type Command = {
  handler: (args: string[], ctx: unknown) => Promise<void> | void;
};

function makePi() {
  const commands = new Map<string, Command>();
  const events = new Map<string, (event: unknown, ctx: unknown) => unknown>();
  let tool: any;
  const pi = {
    on: (name: string, handler: (event: unknown, ctx: unknown) => unknown) =>
      events.set(name, handler),
    registerTool: (registeredTool: unknown) => {
      tool = registeredTool;
    },
    registerCommand: (name: string, command: Command) =>
      commands.set(name, command),
  };
  todoExtension(pi as never);
  return { commands, events, tool };
}

const theme = {
  fg: (_name: string, value: string) => value,
  bold: (value: string) => value,
};

describe("todo.ts / /todos command", () => {
  it("keeps registering /todos under its original name (plan-mode's rename to /plan-todos must not collide)", () => {
    const { commands } = makePi();

    expect(commands.has("todos")).toBe(true);
    expect(commands.has("plan-todos")).toBe(false);
  });
});

describe("todo tool resilience", () => {
  it("renders malformed result details as the tool's text instead of returning undefined", () => {
    const { tool } = makePi();

    const rendered = tool.renderResult(
      {
        content: [{ type: "text", text: "Invalid action" }],
        details: {},
        isError: true,
      },
      { expanded: false },
      theme,
      {},
    );

    expect(rendered.text).toBe("Invalid action");
  });

  it("ignores malformed result details while reconstructing session state", async () => {
    const { events, tool } = makePi();
    const first = await tool.execute("first", { action: "add", text: "keep" });
    const sessionStart = events.get("session_start");

    await sessionStart?.(
      {},
      {
        sessionManager: {
          getBranch: () => [
            {
              type: "message",
              message: { role: "toolResult", toolName: "todo", details: first.details },
            },
            {
              type: "message",
              message: { role: "toolResult", toolName: "todo", details: {}, isError: true },
            },
          ],
        },
      },
    );

    const second = await tool.execute("second", { action: "add", text: "still works" });
    expect(second.details.todos).toEqual([
      { id: 1, text: "keep", done: false },
      { id: 2, text: "still works", done: false },
    ]);
  });
});
