import { spawn, type ChildProcess } from "node:child_process";
import { homedir } from "node:os";
import { isAbsolute, relative, resolve } from "node:path";
import type { HookCommand } from "./schema.js";

export const DEFAULT_OUTPUT_LIMIT_BYTES = 64 * 1024;
const KILL_GRACE_MILLISECONDS = 100;
const COMMON_HOOK_ENVIRONMENT_VARIABLES = new Set([
  "PATH", "HOME", "TMPDIR", "TMP", "TEMP", "LANG", "LC_ALL", "LC_CTYPE",
  "LC_COLLATE", "LC_MESSAGES", "LC_MONETARY", "LC_NUMERIC", "LC_TIME", "LC_PAPER",
  "LC_NAME", "LC_ADDRESS", "LC_TELEPHONE", "LC_MEASUREMENT", "LC_IDENTIFICATION",
]);
const WINDOWS_HOOK_ENVIRONMENT_VARIABLES = new Set([
  "COMSPEC", "PATHEXT", "SYSTEMROOT", "WINDIR", "USERPROFILE", "HOMEDRIVE", "HOMEPATH",
  "APPDATA", "LOCALAPPDATA", "PROGRAMDATA",
]);

export interface ProcessResult {
  exitCode: number | null;
  signal: string | null;
  stdout: string;
  stderr: string;
}

export interface RunProcessOptions {
  packageRoot: string;
  input: unknown;
  timeoutMilliseconds: number;
  signal?: AbortSignal;
  outputLimitBytes?: number;
  environment?: readonly string[];
}

export type ProcessRunner = (command: HookCommand, options: RunProcessOptions) => Promise<ProcessResult>;

export function resolvePackageFile(packageRoot: string, packageFile: string): string {
  if (packageFile.length === 0 || isAbsolute(packageFile) || packageFile.includes("\\")) {
    throw new Error(`invalid package-file path ${JSON.stringify(packageFile)}`);
  }
  const segments = packageFile.split("/");
  if (segments.some((segment) => segment === "" || segment === "." || segment === "..")) {
    throw new Error(`invalid package-file path ${JSON.stringify(packageFile)}`);
  }
  const root = resolve(packageRoot);
  const candidate = resolve(root, ...segments);
  const contained = relative(root, candidate);
  if (contained === "" || contained === ".." || contained.startsWith(`..${pathSeparator()}`) || isAbsolute(contained)) {
    throw new Error(`package-file path escapes package root: ${JSON.stringify(packageFile)}`);
  }
  return candidate;
}

export const runProcess: ProcessRunner = async (command, options) => {
  const limit = options.outputLimitBytes ?? DEFAULT_OUTPUT_LIMIT_BYTES;
  if (!Number.isSafeInteger(limit) || limit <= 0) throw new Error("output limit must be a positive integer");
  const invocation = invocationFor(command, options.packageRoot);
  if (options.signal?.aborted) throw abortError(options.signal.reason);

  return await new Promise<ProcessResult>((resolvePromise, reject) => {
    let child: ChildProcess;
    try {
      child = spawn(invocation.program, invocation.arguments, {
        cwd: options.packageRoot,
        detached: process.platform !== "win32",
        env: hookEnvironment(options.environment),
        stdio: ["pipe", "pipe", "pipe"],
      });
    } catch (error) {
      reject(error);
      return;
    }

    let stdoutBytes = 0;
    let stderrBytes = 0;
    const stdout: Uint8Array[] = [];
    const stderr: Uint8Array[] = [];
    let settled = false;
    let failure: Error | undefined;
    let terminationStarted = false;
    let killTimer: ReturnType<typeof setTimeout> | undefined;

    const cleanup = (clearKillTimer = true): void => {
      clearTimeout(timeoutTimer);
      if (clearKillTimer && killTimer !== undefined) clearTimeout(killTimer);
      options.signal?.removeEventListener("abort", onAbort);
    };
    const fail = (error: Error): void => {
      if (settled || failure !== undefined) return;
      failure = error;
      terminate();
      cleanup(false);
    };
    const terminate = (): void => {
      if (terminationStarted) return;
      terminationStarted = true;
      signalChild(child, "SIGTERM");
      killTimer = setTimeout(() => signalChild(child, "SIGKILL"), KILL_GRACE_MILLISECONDS);
    };
    const collect = (target: Uint8Array[], chunk: Uint8Array, stream: "stdout" | "stderr"): void => {
      if (failure !== undefined) return;
      const next = (stream === "stdout" ? stdoutBytes : stderrBytes) + chunk.byteLength;
      if (stream === "stdout") stdoutBytes = next; else stderrBytes = next;
      if (next > limit) {
        fail(new Error(`${stream} exceeded ${limit} byte limit`));
        return;
      }
      target.push(chunk);
    };
    const onAbort = (): void => fail(abortError(options.signal?.reason));
    const timeoutTimer = setTimeout(() => fail(new Error(`hook timed out after ${options.timeoutMilliseconds}ms`)), options.timeoutMilliseconds);

    options.signal?.addEventListener("abort", onAbort, { once: true });
    child.stdout?.on("data", (chunk) => collect(stdout, chunk, "stdout"));
    child.stderr?.on("data", (chunk) => collect(stderr, chunk, "stderr"));
    child.once("error", fail);
    child.stdin.once("error", fail);
    child.once("close", (exitCode, signal) => {
      if (settled) return;
      settled = true;
      cleanup();
      if (failure !== undefined) {
        reject(failure);
        return;
      }
      resolvePromise({
        exitCode,
        signal,
        stdout: decodeChunks(stdout, stdoutBytes),
        stderr: decodeChunks(stderr, stderrBytes),
      });
    });
    child.stdin.end(`${JSON.stringify(options.input)}\n`);
  });
};

export function hookEnvironment(
  requested: readonly string[] = [],
  parent: Readonly<Record<string, string | undefined>> = process.env,
): Record<string, string> {
  const allowed = new Set(COMMON_HOOK_ENVIRONMENT_VARIABLES);
  if (process.platform === "win32") {
    for (const name of WINDOWS_HOOK_ENVIRONMENT_VARIABLES) allowed.add(name);
  }
  for (const name of requested) allowed.add(canonicalEnvironmentName(name));

  const environment: Record<string, string> = {};
  for (const [name, value] of Object.entries(parent)) {
    const canonicalName = canonicalEnvironmentName(name);
    if (value !== undefined && allowed.has(canonicalName)) environment[canonicalName] = value;
  }
  if (environment.HOME === undefined) {
    const fallback = homedir();
    if (fallback !== "") environment.HOME = fallback;
  }
  return environment;
}

function canonicalEnvironmentName(name: string): string {
  return process.platform === "win32" ? name.toUpperCase() : name;
}

function invocationFor(command: HookCommand, packageRoot: string): { program: string; arguments: string[] } {
  if (command.mode === "shell") {
    return process.platform === "win32"
      ? { program: "cmd.exe", arguments: ["/d", "/s", "/c", command.shellCommand] }
      : { program: "/bin/sh", arguments: ["-c", command.shellCommand] };
  }
  return {
    program: command.program,
    arguments: command.arguments.map((argument) =>
      "literal" in argument ? argument.literal : resolvePackageFile(packageRoot, argument.packageFile)),
  };
}

function signalChild(child: ChildProcess, signal: "SIGTERM" | "SIGKILL"): void {
  try {
    if (process.platform !== "win32" && child.pid !== undefined) process.kill(-child.pid, signal);
    else child.kill(signal);
  } catch {
    try { child.kill(signal); } catch { /* The process already exited. */ }
  }
}

function decodeChunks(chunks: Uint8Array[], byteLength: number): string {
  const all = new Uint8Array(byteLength);
  let offset = 0;
  for (const chunk of chunks) {
    all.set(chunk, offset);
    offset += chunk.byteLength;
  }
  return new TextDecoder("utf-8", { fatal: false }).decode(all);
}

function abortError(reason: unknown): Error {
  const error = new Error(typeof reason === "string" ? reason : "hook cancelled");
  error.name = "AbortError";
  return error;
}

function pathSeparator(): string {
  return process.platform === "win32" ? "\\" : "/";
}
