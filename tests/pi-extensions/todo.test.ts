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
  const pi = {
    on: () => {},
    registerTool: () => {},
    registerCommand: (name: string, command: Command) =>
      commands.set(name, command),
  };
  todoExtension(pi as never);
  return { commands };
}

describe("todo.ts / /todos command", () => {
  it("keeps registering /todos under its original name (plan-mode's rename to /plan-todos must not collide)", () => {
    const { commands } = makePi();

    expect(commands.has("todos")).toBe(true);
    expect(commands.has("plan-todos")).toBe(false);
  });
});
