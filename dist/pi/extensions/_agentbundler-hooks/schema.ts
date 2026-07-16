export const SCHEMA_VERSION = 1;
export const MAX_TIMEOUT_MILLISECONDS = 600_000;

export type HookEvent =
  | "session-start"
  | "session-end"
  | "prompt-submit"
  | "pre-tool"
  | "post-tool"
  | "post-tool-failure"
  | "stop"
  | "pre-compact"
  | "post-compact";

export type ToolCategory =
  | "command"
  | "read"
  | "write"
  | "edit"
  | "search"
  | "web"
  | "task"
  | "mcp"
  | "other";

export type HookArgument =
  | { literal: string }
  | { packageFile: string };

export type HookCommand =
  | { mode: "exec"; program: string; arguments: HookArgument[] }
  | { mode: "shell"; shellCommand: string; arguments: [] };

export interface HookDescriptor {
  identity: string;
  event: HookEvent;
  matcher?: { tools: ToolCategory[] };
  handler: HookCommand;
  timeoutMilliseconds: number;
  asynchronous: boolean;
  failurePolicy: "open" | "closed";
  order: number;
}

export interface HookConfigV1 {
  version: 1;
  hooks: HookDescriptor[];
}

type JSONObject = Record<string, unknown>;

const EVENTS = new Set<HookEvent>([
  "session-start",
  "session-end",
  "prompt-submit",
  "pre-tool",
  "post-tool",
  "post-tool-failure",
  "stop",
  "pre-compact",
  "post-compact",
]);
const TOOL_CATEGORIES = new Set<ToolCategory>([
  "command", "read", "write", "edit", "search", "web", "task", "mcp", "other",
]);

export function decodeConfig(value: unknown): HookConfigV1 {
  const object = asObject(value, "config");
  exactKeys(object, ["version", "hooks"], "config");
  if (!Number.isInteger(object.version)) {
    throw new Error("config.version must be an integer");
  }
  if (object.version !== SCHEMA_VERSION) {
    throw new Error(`unsupported hook schema version ${String(object.version)}; expected ${SCHEMA_VERSION}`);
  }
  if (!Array.isArray(object.hooks)) {
    throw new Error("config.hooks must be an array");
  }
  const identities = new Set<string>();
  const hooks = object.hooks.map((hook, index) => decodeHook(hook, index));
  for (const hook of hooks) {
    if (identities.has(hook.identity)) {
      throw new Error(`duplicate hook identity ${JSON.stringify(hook.identity)}`);
    }
    identities.add(hook.identity);
  }
  hooks.sort((left, right) => left.order - right.order || compareUTF8(left.identity, right.identity));
  return { version: SCHEMA_VERSION, hooks };
}

function decodeHook(value: unknown, index: number): HookDescriptor {
  const field = `config.hooks[${index}]`;
  const object = asObject(value, field);
  // location is source evidence used by Go and deliberately ignored by this runtime.
  exactKeys(object, ["identity", "location", "event", "matcher", "handler", "timeoutMilliseconds", "asynchronous", "failurePolicy", "order"], field);
  const identity = nonEmptyString(object.identity, `${field}.identity`);
  if (!EVENTS.has(object.event as HookEvent)) {
    throw new Error(`${field}.event is unsupported`);
  }
  const event = object.event as HookEvent;
  const timeoutMilliseconds = integer(object.timeoutMilliseconds, `${field}.timeoutMilliseconds`);
  if (timeoutMilliseconds <= 0 || timeoutMilliseconds > MAX_TIMEOUT_MILLISECONDS) {
    throw new Error(`${field}.timeoutMilliseconds must be between 1 and ${MAX_TIMEOUT_MILLISECONDS}`);
  }
  if (typeof object.asynchronous !== "boolean") {
    throw new Error(`${field}.asynchronous must be a boolean`);
  }
  const asynchronousEvents = new Set<HookEvent>(["session-end", "post-tool", "post-tool-failure", "pre-compact", "post-compact"]);
  if (object.asynchronous && !asynchronousEvents.has(event)) {
    throw new Error(`${field}.asynchronous is not valid for ${event} hooks`);
  }
  if (object.failurePolicy !== "open" && object.failurePolicy !== "closed") {
    throw new Error(`${field}.failurePolicy must be open or closed`);
  }
  if (object.failurePolicy === "closed" && event !== "pre-tool") {
    throw new Error(`${field}.failurePolicy closed is enforceable only for pre-tool hooks, not ${event}`);
  }
  const order = integer(object.order, `${field}.order`);
  if (order < 0) throw new Error(`${field}.order must not be negative`);
  const hook: HookDescriptor = {
    identity,
    event,
    handler: decodeCommand(object.handler, `${field}.handler`),
    timeoutMilliseconds,
    asynchronous: object.asynchronous,
    failurePolicy: object.failurePolicy,
    order,
  };
  if (object.matcher !== undefined && object.matcher !== null) {
    if (event !== "pre-tool" && event !== "post-tool" && event !== "post-tool-failure") {
      throw new Error(`${field}.matcher is only valid for tool hooks`);
    }
    hook.matcher = decodeMatcher(object.matcher, `${field}.matcher`);
  }
  return hook;
}

function decodeMatcher(value: unknown, field: string): { tools: ToolCategory[] } {
  const object = asObject(value, field);
  exactKeys(object, ["tools"], field);
  if (!Array.isArray(object.tools) || object.tools.length === 0) {
    throw new Error(`${field}.tools must be a non-empty array`);
  }
  const tools = object.tools.map((tool, index) => {
    if (!TOOL_CATEGORIES.has(tool as ToolCategory)) {
      throw new Error(`${field}.tools[${index}] is unsupported`);
    }
    return tool as ToolCategory;
  });
  if (new Set(tools).size !== tools.length) {
    throw new Error(`${field}.tools contains a duplicate`);
  }
  return { tools };
}

function decodeCommand(value: unknown, field: string): HookCommand {
  const object = asObject(value, field);
  if (object.mode === "exec") {
    exactKeys(object, ["mode", "program", "arguments"], field);
    const program = nonEmptyString(object.program, `${field}.program`);
    if (program.trim() !== program || /[\0/\\]/u.test(program)) {
      throw new Error(`${field}.program must be a bare program name`);
    }
    if (!Array.isArray(object.arguments)) {
      throw new Error(`${field}.arguments must be an array`);
    }
    const arguments_ = object.arguments.map((argument, index) => decodeArgument(argument, `${field}.arguments[${index}]`));
    return { mode: "exec", program, arguments: arguments_ };
  }
  if (object.mode === "shell") {
    exactKeys(object, ["mode", "arguments", "shellCommand"], field);
    if (!Array.isArray(object.arguments) || object.arguments.length !== 0) {
      throw new Error(`${field}.arguments must be empty in shell mode`);
    }
    const shellCommand = nonEmptyString(object.shellCommand, `${field}.shellCommand`);
    if (shellCommand.includes("\0")) throw new Error(`${field}.shellCommand contains NUL`);
    return { mode: "shell", shellCommand, arguments: [] };
  }
  throw new Error(`${field}.mode must be exec or shell`);
}

function decodeArgument(value: unknown, field: string): HookArgument {
  const object = asObject(value, field);
  const keys = Object.keys(object);
  if (keys.length !== 1 || (keys[0] !== "literal" && keys[0] !== "packageFile")) {
    throw new Error(`${field} must contain exactly one of literal or packageFile`);
  }
  if (keys[0] === "literal") {
    const literal = stringValue(object.literal, `${field}.literal`);
    if (literal.includes("\0")) throw new Error(`${field}.literal contains NUL`);
    return { literal };
  }
  const packageFile = nonEmptyString(object.packageFile, `${field}.packageFile`);
  validatePackageFileSyntax(packageFile, `${field}.packageFile`);
  return { packageFile };
}

function validatePackageFileSyntax(value: string, field: string): void {
  if (value.startsWith("/") || value.includes("\\") || value.split("/").some((segment) => segment === "" || segment === "." || segment === "..")) {
    throw new Error(`${field} must be a contained relative path`);
  }
}

function compareUTF8(left: string, right: string): number {
  const leftBytes = new TextEncoder().encode(left);
  const rightBytes = new TextEncoder().encode(right);
  const length = Math.min(leftBytes.length, rightBytes.length);
  for (let index = 0; index < length; index++) {
    if (leftBytes[index] !== rightBytes[index]) return leftBytes[index]! - rightBytes[index]!;
  }
  return leftBytes.length - rightBytes.length;
}

function asObject(value: unknown, field: string): JSONObject {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    throw new Error(`${field} must be an object`);
  }
  return value as JSONObject;
}

function exactKeys(object: JSONObject, allowed: readonly string[], field: string): void {
  const allowedSet = new Set(allowed);
  for (const key of Object.keys(object)) {
    if (!allowedSet.has(key)) throw new Error(`${field} contains unknown field ${JSON.stringify(key)}`);
  }
  for (const key of allowed) {
    if (key !== "location" && key !== "matcher" && object[key] === undefined) {
      throw new Error(`${field}.${key} is required`);
    }
  }
}

function nonEmptyString(value: unknown, field: string): string {
  const result = stringValue(value, field);
  if (result.length === 0) throw new Error(`${field} must not be empty`);
  return result;
}
function stringValue(value: unknown, field: string): string {
  if (typeof value !== "string") throw new Error(`${field} must be a string`);
  return value;
}
function integer(value: unknown, field: string): number {
  if (!Number.isSafeInteger(value)) throw new Error(`${field} must be an integer`);
  return value as number;
}
