import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { createPiHookRuntime, type PiExtensionAPI } from "./_agentbundler-hooks/index.js";

const packageRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const config = JSON.parse(readFileSync(resolve(packageRoot, "hooks/hooks.v1.json"), "utf8")) as unknown;

export default function agentBundlerHooks(pi: PiExtensionAPI): void {
  createPiHookRuntime(pi, config, { packageRoot });
}
