import { matchesTool } from "./matcher.js";
import { runProcess, type ProcessRunner } from "./process.js";
import { decodeConfig, type HookConfigV1, type HookDescriptor, type HookEvent } from "./schema.js";

export interface PiEventContext {
  signal?: AbortSignal;
}

export type PiEventHandler = (event: Record<string, unknown>, context: PiEventContext) => Promise<unknown> | unknown;

export interface PiExtensionAPI {
  on(event: string, handler: PiEventHandler): void;
}

export interface RuntimeOptions {
  packageRoot: string;
  runner?: ProcessRunner;
  outputLimitBytes?: number;
  onError?: (error: Error, hook: HookDescriptor) => void;
}

export interface PiHookRuntime {
  readonly config: HookConfigV1;
  shutdown(): Promise<void>;
}

type HookDecision =
  | { decision: "allow" }
  | { decision: "deny"; reason?: string }
  | { decision: "rewrite-input"; input: Record<string, unknown> };

const PI_EVENTS: ReadonlyArray<readonly [string, HookEvent]> = [
  ["session_start", "session-start"],
  ["session_shutdown", "session-end"],
  ["before_agent_start", "prompt-submit"],
  ["tool_call", "pre-tool"],
  ["tool_result", "post-tool"],
  ["agent_end", "stop"],
  ["session_before_compact", "pre-compact"],
  ["session_compact", "post-compact"],
];

export function createPiHookRuntime(pi: PiExtensionAPI, value: unknown, options: RuntimeOptions): PiHookRuntime {
  if (options.packageRoot.length === 0) throw new Error("packageRoot must not be empty");
  const config = decodeConfig(value);
  const runner = options.runner ?? runProcess;
  const active = new Set<{ controller: AbortController; done: Promise<void> }>();
  let closed = false;
  let shutdownRequested = false;
  let shutdownPromise: Promise<void> | undefined;

  const invoke = async (hook: HookDescriptor, event: Record<string, unknown>, context: PiEventContext): Promise<HookDecision> => {
    const controller = new AbortController();
    const cancel = (): void => controller.abort(context.signal?.reason);
    if (context.signal?.aborted) cancel();
    else context.signal?.addEventListener("abort", cancel, { once: true });

    let finish!: () => void;
    const done = new Promise<void>((resolve) => { finish = resolve; });
    const invocation = { controller, done };
    active.add(invocation);
    try {
      const result = await runner(hook.handler, {
        packageRoot: options.packageRoot,
        input: { event: hook.event, hook: hook.identity, piEvent: event },
        timeoutMilliseconds: hook.timeoutMilliseconds,
        signal: controller.signal,
        ...(options.outputLimitBytes === undefined ? {} : { outputLimitBytes: options.outputLimitBytes }),
      });
      if (result.exitCode !== 0) {
        const detail = result.stderr.trim();
        throw new Error(`hook exited with code ${String(result.exitCode)}${detail === "" ? "" : `: ${detail}`}`);
      }
      return decodeOutput(result.stdout);
    } finally {
      context.signal?.removeEventListener("abort", cancel);
      active.delete(invocation);
      finish();
    }
  };

  const dispatchHooks = async (
    hooks: HookDescriptor[],
    event: Record<string, unknown>,
    context: PiEventContext,
    allowAfterClosure = false,
  ): Promise<unknown> => {
    for (const hook of hooks) {
      if (closed && !allowAfterClosure) return undefined;
      if (hook.event === "post-tool" && event.isError === true) continue;
      if (hook.event === "post-tool-failure" && event.isError !== true) continue;
      const toolName = typeof event.toolName === "string" ? event.toolName : "";
      if ((hook.event === "pre-tool" || hook.event === "post-tool" || hook.event === "post-tool-failure") &&
          !matchesTool(hook, toolName)) continue;

      if (hook.asynchronous) {
        void invoke(hook, snapshot(event), context).catch((error: unknown) => report(error, hook, options.onError));
        continue;
      }

      let decision: HookDecision;
      try {
        decision = await invoke(hook, snapshot(event), context);
      } catch (error) {
        report(error, hook, options.onError);
        if (hook.failurePolicy === "open") continue;
        if (hook.event === "pre-tool") return { block: true, reason: errorMessage(error) };
        throw error;
      }

      if (hook.event !== "pre-tool") {
        if (decision.decision !== "allow") {
          const error = new Error(`${decision.decision} is only valid for pre-tool hooks`);
          report(error, hook, options.onError);
          if (hook.failurePolicy === "closed") throw error;
        }
        continue;
      }
      if (decision.decision === "deny") return { block: true, ...(decision.reason === undefined ? {} : { reason: decision.reason }) };
      if (decision.decision === "rewrite-input") {
        const input = event.input;
        if (!isPlainRecord(input)) {
          const error = new Error("Pi tool input is not a plain object; refusing rewrite");
          report(error, hook, options.onError);
          if (hook.failurePolicy === "closed") return { block: true, reason: error.message };
          continue;
        }
        replaceRecord(input, decision.input);
      }
    }
    return undefined;
  };

  for (const [piEvent, portableEvent] of PI_EVENTS) {
    const hooks = config.hooks.filter((hook) => hook.event === portableEvent ||
      (piEvent === "tool_result" && hook.event === "post-tool-failure"));
    if (hooks.length === 0 && piEvent !== "session_shutdown") continue;

    pi.on(piEvent, async (event, context) => {
      if (piEvent !== "session_shutdown") {
        if (closed) return undefined;
        return await dispatchHooks(hooks, event, context);
      }
      if (shutdownPromise !== undefined) {
        await shutdownPromise;
        return undefined;
      }
      closed = true;
      shutdownPromise = (async () => {
        await cancelActive("session shutdown");
        if (shutdownRequested) return;
        try {
          await dispatchHooks(hooks, event, context, true);
        } finally {
          await waitForActive();
        }
      })();
      await shutdownPromise;
      return undefined;
    });
  }

  async function cancelActive(reason: string): Promise<void> {
    const pending = [...active];
    for (const invocation of pending) invocation.controller.abort(reason);
    await Promise.all(pending.map((invocation) => invocation.done));
  }

  async function waitForActive(): Promise<void> {
    const pending = [...active];
    await Promise.all(pending.map((invocation) => invocation.done));
  }

  function shutdown(): Promise<void> {
    shutdownRequested = true;
    if (shutdownPromise !== undefined) {
      for (const invocation of active) invocation.controller.abort("runtime shutdown");
      return shutdownPromise;
    }
    closed = true;
    shutdownPromise = cancelActive("runtime shutdown");
    return shutdownPromise;
  }

  return { config, shutdown };
}

function decodeOutput(stdout: string): HookDecision {
  const text = stdout.trim();
  if (text === "") return { decision: "allow" };
  let value: unknown;
  try { value = JSON.parse(text); } catch { throw new Error("hook stdout must be one JSON object"); }
  if (!isPlainRecord(value) || typeof value.decision !== "string") {
    throw new Error("hook output must contain a decision");
  }
  if (value.decision === "allow") {
    exactOutputKeys(value, ["decision"]);
    return { decision: "allow" };
  }
  if (value.decision === "deny") {
    exactOutputKeys(value, ["decision", "reason"]);
    if (value.reason !== undefined && typeof value.reason !== "string") throw new Error("deny reason must be a string");
    return { decision: "deny", ...(value.reason === undefined ? {} : { reason: value.reason }) };
  }
  if (value.decision === "rewrite-input") {
    exactOutputKeys(value, ["decision", "input"]);
    if (!isSafeJSONRecord(value.input)) throw new Error("rewrite input must be a safe JSON object");
    return { decision: "rewrite-input", input: value.input };
  }
  throw new Error(`unsupported hook decision ${JSON.stringify(value.decision)}`);
}

function exactOutputKeys(value: Record<string, unknown>, allowed: readonly string[]): void {
  const set = new Set(allowed);
  if (Object.keys(value).some((key) => !set.has(key))) throw new Error("hook output contains an unknown field");
  if (value.decision === "rewrite-input" && !("input" in value)) throw new Error("rewrite input is required");
}

function isPlainRecord(value: unknown): value is Record<string, unknown> {
  if (value === null || typeof value !== "object" || Array.isArray(value)) return false;
  const prototype = Object.getPrototypeOf(value);
  return prototype === Object.prototype || prototype === null;
}

function isSafeJSONRecord(value: unknown): value is Record<string, unknown> {
  return isPlainRecord(value) && safeJSONValue(value, new Set<object>());
}

function safeJSONValue(value: unknown, seen: Set<object>): boolean {
  if (value === null || typeof value === "string" || typeof value === "boolean") return true;
  if (typeof value === "number") return Number.isFinite(value);
  if (typeof value !== "object" || seen.has(value)) return false;
  seen.add(value);
  if (Array.isArray(value)) return value.every((item) => safeJSONValue(item, seen));
  if (!isPlainRecord(value)) return false;
  return Object.entries(value).every(([key, item]) =>
    key !== "__proto__" && key !== "prototype" && key !== "constructor" && safeJSONValue(item, seen));
}

function replaceRecord(target: Record<string, unknown>, replacement: Record<string, unknown>): void {
  const validatedCopy = JSON.parse(JSON.stringify(replacement)) as Record<string, unknown>;
  for (const key of Object.keys(target)) delete target[key];
  Object.assign(target, validatedCopy);
}

function snapshot(event: Record<string, unknown>): Record<string, unknown> {
  try { return JSON.parse(JSON.stringify(event)) as Record<string, unknown>; }
  catch { return { type: event.type }; }
}

function report(error: unknown, hook: HookDescriptor, reporter: RuntimeOptions["onError"]): void {
  reporter?.(error instanceof Error ? error : new Error(String(error)), hook);
}
function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}
