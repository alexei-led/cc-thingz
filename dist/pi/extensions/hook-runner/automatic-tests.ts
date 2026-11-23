import { readFileSync } from "node:fs";
import { join } from "node:path";
import { CONFIG_DIR_NAME, type ExtensionContext } from "@earendil-works/pi-coding-agent";

export function configureAutomaticTests(ctx: Pick<ExtensionContext, "cwd" | "isProjectTrusted">): void {
	let enabled = false;
	try {
		const settings: unknown = ctx.isProjectTrusted() ? JSON.parse(readFileSync(join(ctx.cwd, CONFIG_DIR_NAME, "settings.json"), "utf8")) : null;
		enabled = typeof settings === "object" && settings !== null && (settings as Record<string, unknown>).automaticTests === true;
	} catch {
		// Missing or invalid settings leave automatic tests disabled.
	}
	process.env.SKIP_TESTS = enabled ? "0" : "1";
}
