import { expect, it } from "bun:test";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { inspectShellWarnings } from "../../../src/plugins/pi/extensions/extensions/shared/shell-warnings.js";

it("checks obvious warning text when input exceeds the parse limit", () => {
	const padding = "x".repeat(256 * 1024);
	expect(inspectShellWarnings(padding).dangerous).toBe(false);
	expect(inspectShellWarnings(`${padding}; sudo true`).dangerous).toBe(true);
});

it("returns promptly for deeply nested unterminated substitutions", () => {
	const modulePath = fileURLToPath(new URL("../../../src/plugins/pi/extensions/extensions/shared/shell-warnings.ts", import.meta.url));
	const openers = ["$(", "${"];
	const source = `import { inspectShellWarnings } from ${JSON.stringify(modulePath)};
for (const opener of ${JSON.stringify(openers)}) {
  inspectShellWarnings("echo " + opener.repeat(40));
}
inspectShellWarnings("echo " + "$(x ".repeat(5000) + ")".repeat(5000));
inspectShellWarnings("find . " + "-exec echo x + ".repeat(5000));
console.log("complete");`;
	const result = spawnSync(process.execPath, ["-e", source], {
		encoding: "utf8",
		timeout: 3000,
		killSignal: "SIGKILL",
	});
	expect(result.error).toBeUndefined();
	expect(result.status).toBe(0);
	expect(result.stdout.trim()).toBe("complete");
}, 8000);
