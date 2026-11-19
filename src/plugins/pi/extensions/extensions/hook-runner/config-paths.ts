/**
 * Filesystem paths and placeholder constants used across hook-runner config.
 */

import { getAgentDir } from "@earendil-works/pi-coding-agent";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
// dist/pi/extensions/hook-runner/config-paths.ts → ../../hooks → dist/pi/hooks
export const HOOKS_DIR = join(__dirname, "..", "..", "hooks");
export const BUNDLED_HOOKS_CONFIG_PATH = join(__dirname, "..", "hooks.json");
export const PI_HOOKS_DIR_PLACEHOLDER = "${PI_HOOKS_DIR}";
export const PKG_DIR_PLACEHOLDER = "${PKG_DIR}";
export const FORCED_RELOAD_DEBOUNCE_MS = 500;

export const agentDir = getAgentDir;

export function projectHooksConfigPath(cwd: string): string {
	return join(cwd, ".pi", "hooks.json");
}

export function globalHooksConfigPath(): string {
	return join(agentDir(), "hooks.json");
}
