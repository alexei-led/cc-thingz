import { spawn } from "node:child_process";
import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { expect, it } from "bun:test";

it("keeps questions direct in native Code Mode only and supports RPC select", async () => {
	const dir = mkdtempSync(join(tmpdir(), "question-rpc-"));
	const agentDir = join(dir, "agent");
	mkdirSync(agentDir);
	writeFileSync(join(agentDir, "settings.json"), JSON.stringify({ defaultTools: ["+codemode"], codemode: { mode: "only" } }));
	const questionPath = join(process.cwd(), "src/plugins/pi/extensions/extensions/ask-user-question.ts");
	const fixture = join(dir, "fixture.ts");
	writeFileSync(
		fixture,
		`
import ask from ${JSON.stringify(questionPath)};
export default function (pi) {
  let questionTool;
  let callable = [];
  ask({ registerTool(tool) {
    questionTool = tool;
    pi.registerTool({ ...tool, prepareLoadout(loadout) { callable = loadout.callable.map(t => t.name); } });
  } });
  pi.registerCommand("question-contract", { handler: async (_args, ctx) => {
    ctx.ui.notify(JSON.stringify({ exposure: pi.getAllTools().find(t => t.name === "ask_user_question").exposure,
      active: pi.getActiveTools(), callable }));
    const result = await questionTool.execute("contract", { questions: [{ question: "Pick a value", options: [
      { label: "Same", value: "first" }, { label: "Same", value: "second" } ], allowOther: false }] }, undefined, undefined, ctx);
    ctx.ui.notify(JSON.stringify({ result: result.details }));
  } });
}
`,
	);
	const cli = join(process.cwd(), "node_modules/@earendil-works/pi-coding-agent/dist/bundle/cli.js");
	const child = spawn("node", [cli, "--mode", "rpc", "--no-session", "--no-skills", "--no-prompt-templates", "--no-themes", "-e", fixture], {
		cwd: dir,
		env: { PATH: process.env.PATH, HOME: dir, PI_CODING_AGENT_DIR: agentDir, PI_OFFLINE: "1" },
		stdio: ["pipe", "pipe", "pipe"],
	});
	try {
		const evidence: Record<string, unknown>[] = [];
		await new Promise<void>((resolve, reject) => {
			let buffered = "";
			let errors = "";
			const timeout = setTimeout(() => reject(new Error(`RPC question timed out: ${errors}`)), 15000);
			child.stderr.on("data", (chunk) => {
				errors += chunk.toString();
			});
			child.on("error", (error) => {
				clearTimeout(timeout);
				reject(error);
			});
			child.on("exit", (code) => {
				clearTimeout(timeout);
				reject(new Error(`RPC exited ${code}: ${errors}`));
			});
			child.stdout.on("data", (chunk) => {
				buffered += chunk.toString();
				let end: number;
				while ((end = buffered.indexOf("\n")) >= 0) {
					const line = buffered.slice(0, end);
					buffered = buffered.slice(end + 1);
					if (!line.trim()) continue;
					try {
						const event = JSON.parse(line);
						errors += JSON.stringify({ type: event.type, command: event.command, success: event.success, error: event.error, method: event.method }) + "\n";
						if (event.type === "response" && event.command === "get_commands") {
							expect(event.success).toBe(true);
							expect(event.data.commands.some((command: { name: string }) => command.name === "question-contract")).toBe(true);
							child.stdin.write(JSON.stringify({ type: "prompt", message: "/question-contract" }) + "\n");
						} else if (event.type === "agent_start" || event.type === "message_start") {
							throw new Error("RPC contract test must not start model generation");
						} else if (event.type === "extension_error") {
							clearTimeout(timeout);
							reject(new Error(event.error));
						} else if (event.type === "extension_ui_request" && event.method === "select") {
							evidence.push({ choices: event.options });
							child.stdin.write(JSON.stringify({ type: "extension_ui_response", id: event.id, value: event.options[1] }) + "\n");
						} else if (event.type === "extension_ui_request" && event.method === "notify") {
							const data = JSON.parse(event.message);
							evidence.push(data);
							if (data.result) {
								clearTimeout(timeout);
								resolve();
							}
						}
					} catch (error) {
						clearTimeout(timeout);
						reject(error);
					}
				}
			});
			child.stdin.write('{"type":"get_commands"}\n');
		});
		expect(evidence[0]).toMatchObject({ exposure: "model-only", active: expect.arrayContaining(["codemode", "ask_user_question"]) });
		expect(evidence[0].callable).not.toContain("ask_user_question");
		expect(evidence[1]).toEqual({ choices: ["1. Same", "2. Same"] });
		expect(evidence[2]).toMatchObject({ result: { cancelled: false, answers: [{ answers: [{ label: "Same", value: "second", source: "option" }] }] } });
	} finally {
		child.stdin.end();
		child.kill();
		await new Promise<void>((resolve) => {
			if (child.exitCode !== null || child.signalCode !== null) resolve();
			else child.once("exit", () => resolve());
		});
		rmSync(dir, { recursive: true, force: true });
	}
}, 20000);
