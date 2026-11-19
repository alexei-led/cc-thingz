import { afterEach, describe, expect, it, spyOn } from "bun:test";
import { chmodSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { createAssistantMessageEventStream, type AssistantMessage } from "@earendil-works/pi-ai";
import { getModel } from "@earendil-works/pi-ai/compat";
import {
	createAgentSession,
	DefaultResourceLoader,
	ModelRuntime,
	SessionManager,
	SettingsManager,
	type ExtensionFactory,
	type ExtensionUIContext,
} from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";
import permissionGate from "../../../src/plugins/pi/extensions/extensions/permission-gate.js";
import hookRunner from "../../../src/plugins/pi/extensions/extensions/hook-runner/index.js";

const oldAgentDir = process.env.PI_CODING_AGENT_DIR;
afterEach(() => {
	if (oldAgentDir === undefined) delete process.env.PI_CODING_AGENT_DIR;
	else process.env.PI_CODING_AGENT_DIR = oldAgentDir;
});

const normal = [
	"sed -n 1,120p tools/core/_finding_spend.py; echo '=====ESTIMATE'; sed -n 1,140p tools/core/_facts_finding_estimate.py",
	"rg -n 'def compute_estimate|def .*estimate' tools/core/_finding_estimate.py | head -30",
	"rg -n 'set-finding-estimate|set_finding_estimate|refresh-finding-estimate|finding-estimate' --glob '!node_modules' --glob '!.gitnexus' . | head -40; echo '=== candidate-pricing job'; ls setup/cron/jobs/*/ | head -80",
	"rg -rn --no-heading 'REFLEX_CANDIDATE_PRICING' setup/layers setup/files/skills setup/files/agent-skills setup/cron tools/core/_lib.py 2>/dev/null | cut -c1-200",
	"ls ~/Workspace | head -20; echo '=== customers repo'; ls ~/Workspace/reflex-customers 2>/dev/null | head; echo '=== gcloud'; which gcloud; echo '=== instances'; cat setup/fleet.tsv 2>/dev/null | head -20",
	"node - <<'JS'\nconsole.log('sudo rm -rf fixture');\nJS",
	"node - <<J\"S\"\nconsole.log('sudo');\nJS",
	'printf "%s" "$(rg -F sudo README.md | head -1)"',
	'printf "%s" "${missing:-sudo}"',
	"printf '%s' `printf sudo`",
	"cat <<END\n'$(printf sudo)'\nEND",
	"node - <<<'console.log(\"sudo\")'",
	"printf '%s' 'sudo' | awk '{print $1}' | cut -c1-20",
	"gcloud compute ssh fixture --zone us-central1-a --project doit-reflex --quiet --command 'sudo whoami' 2>&1 | tail -35",
];
const dangerous = [
	"sudo forbidden",
	"rm -rf fixture",
	"rm fixture -rf",
	"/usr/bin/time -f '%E' sudo forbidden",
	"xargs -a fixture-list sudo forbidden",
	"cat <<END\n'$(sudo forbidden)'\nEND",
	"cat <<END\n# $(sudo forbidden)\nEND",
	"chmod 777 fixture",
	"printf ok | sudo forbidden",
	'printf "%s" "$(sudo forbidden)"',
	"echo ${#PATH}; sudo forbidden",
	"find setup -name '*.py' -exec rm -rf {} +",
	"sudo>/dev/null forbidden",
	"cat <<<'fixture'\nsudo forbidden",
	"timeout 5 sudo forbidden",
];
const quote = (value: string) => "'" + value.replaceAll("'", "'\\''") + "'";

describe.each([false, true])("real Pi assistant pipeline, UI=%s", (hasUI) => {
	it.each([false, true])(
		"runs direct/nested tool calls, nested=%s",
		async (nested) => {
			const root = mkdtempSync(join(tmpdir(), "permission-session-"));
			const agentDir = join(root, "agent");
			const marker = join(root, "executed");
			mkdirSync(agentDir);
			mkdirSync(join(root, "bin"));
			writeFileSync(marker, "");
			for (const dir of [
				"tools/core",
				"setup/layers",
				"setup/files/skills",
				"setup/files/agent-skills",
				"setup/cron/jobs/example",
				"Workspace/reflex-customers",
			])
				mkdirSync(join(root, dir), { recursive: true });
			for (const file of ["_finding_spend.py", "_facts_finding_estimate.py", "_finding_estimate.py", "_lib.py"])
				writeFileSync(join(root, "tools/core", file), "def compute_estimate(): pass\n# REFLEX_CANDIDATE_PRICING set-finding-estimate\n");
			writeFileSync(join(root, "setup/fleet.tsv"), "fixture\tzone\n");
			writeFileSync(join(root, "README.md"), "sudo is fixture data\n");
			writeFileSync(join(root, "fixture-list"), "fixture\n");
			for (const name of ["sudo", "rm", "chmod", "git", "fixture-read"]) {
				const file = join(root, "bin", name);
				writeFileSync(file, "#!/bin/sh\nprintf '%s\\n' fixture >> " + quote(marker) + "\nprintf '%s\\n' executed-fixture\n");
				chmodSync(file, 0o700);
			}
			writeFileSync(join(root, "bin/gcloud"), "#!/bin/sh\nprintf '%s\\n' remote-fixture\n");
			chmodSync(join(root, "bin/gcloud"), 0o700);
			writeFileSync(
				join(root, "veto.mjs"),
				`let input="";for await(const chunk of process.stdin)input+=chunk;
if(JSON.parse(input).tool_input.command.includes("hook-veto")) console.log(JSON.stringify({
hookSpecificOutput:{hookEventName:"PermissionRequest",decision:{behavior:"deny",message:"fixture hook veto"}}}));`,
			);
			writeFileSync(
				join(agentDir, "hooks.json"),
				JSON.stringify({
					PermissionRequest: [
						{
							matcher: "Bash",
							hooks: [{ type: "command", command: process.execPath + " " + join(root, "veto.mjs"), timeout: 3 }],
						},
					],
				}),
			);
			writeFileSync(
				join(agentDir, "settings.json"),
				JSON.stringify({
					compaction: { enabled: false },
					retry: { enabled: false },
					shellCommandPrefix: "export HOME=" + quote(root) + "; export PATH=" + quote(join(root, "bin")) + ':"$PATH"',
					permissionGate: { allow: [{ match: "Bash(sudo approved)", headless: true }], deny: [{ match: "Bash(git push)" }] },
				}),
			);
			mkdirSync(join(root, ".pi"));
			writeFileSync(
				join(root, ".pi/settings.json"),
				JSON.stringify({
					permissionGate: {
						allow: [{ match: "Bash(gcloud compute ssh * --zone us-central1-a --project doit-reflex --quiet --command *)", headless: true }],
					},
				}),
			);
			process.env.PI_CODING_AGENT_DIR = agentDir;
			const network = spyOn(globalThis, "fetch").mockImplementation(
				Object.assign(
					async () => {
						throw new Error("Network is forbidden in this fixture");
					},
					{
						preconnect: () => {
							throw new Error("Network is forbidden in this fixture");
						},
					},
				),
			);
			let session: Awaited<ReturnType<typeof createAgentSession>>["session"] | undefined;
			try {
				const settings = SettingsManager.create(root, agentDir, { projectTrusted: true });
				const calls: Array<{ name: string; parent?: string }> = [];
				const observer: ExtensionFactory = (pi) => {
					pi.on("tool_call", async (event) => {
						calls.push({ name: event.toolName, parent: event.parentToolCallId });
					});
					pi.registerTool({
						name: "run_fixture",
						label: "fixture",
						description: "Run a local fixture through the normal tool pipeline.",
						parameters: Type.Object({ command: Type.String() }),
						async execute(_id, params, _signal, _update, ctx) {
							const outcome = await ctx.executeTool("bash", { command: params.command, timeout: 10 });
							return { ...outcome.result, isError: outcome.isError };
						},
					});
				};
				const loader = new DefaultResourceLoader({
					cwd: root,
					agentDir,
					settingsManager: settings,
					noExtensions: true,
					noSkills: true,
					noPromptTemplates: true,
					noThemes: true,
					noContextFiles: true,
					extensionFactories: [observer, hookRunner, permissionGate],
				});
				await loader.reload();
				expect(loader.getExtensions().errors).toEqual([]);
				const runtime = await ModelRuntime.create({
					authPath: join(agentDir, "auth.json"),
					modelsPath: join(agentDir, "models.json"),
					allowModelNetwork: false,
					refreshOnCreate: false,
				});
				await runtime.setRuntimeApiKey("openai", "fixture-only");
				const model = getModel("openai", "gpt-4o-mini");
				if (!model) throw new Error("Fixture model missing");
				({ session } = await createAgentSession({
					cwd: root,
					agentDir,
					settingsManager: settings,
					modelRuntime: runtime,
					model,
					resourceLoader: loader,
					sessionManager: SessionManager.inMemory(root),
					tools: ["bash", "run_fixture"],
				}));
				let command = "";
				let id = 0;
				session.agent.streamFunction = (_model, context) => {
					const tool = context.messages.at(-1)?.role !== "toolResult";
					const message: AssistantMessage = {
						role: "assistant",
						api: model.api,
						provider: model.provider,
						model: model.id,
						timestamp: Date.now(),
						content: tool
							? [{ type: "toolCall", id: "fixture-" + ++id, name: nested ? "run_fixture" : "bash", arguments: { command } }]
							: [{ type: "text", text: "done" }],
						stopReason: tool ? "toolUse" : "stop",
						usage: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, totalTokens: 0, cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, total: 0 } },
					};
					const stream = createAssistantMessageEventStream();
					stream.push({ type: "start", partial: message });
					stream.push({ type: "done", reason: tool ? "toolUse" : "stop", message });
					stream.end();
					return stream;
				};
				let selections = 0;
				let answer = "No";
				// UI is the only adapter stub; policy, hooks, dispatch and shell execution are real.
				const ui = {
					select: async () => {
						selections++;
						return answer;
					},
					notify: () => {},
				} as unknown as ExtensionUIContext;
				await session.bindExtensions(hasUI ? { uiContext: ui } : {});
				const run = async (value: string, blocked: boolean) => {
					command = value;
					await session!.prompt("Run the local test fixture.");
					const result = session!.messages.filter((message) => message.role === "toolResult").at(-1);
					expect(result).toMatchObject({ isError: blocked });
					if (blocked) expect(JSON.stringify(result)).toMatch(/Dangerous command blocked|Blocked by user|fixture hook veto/);
				};
				for (const value of normal) {
					const before = selections;
					await run(value, false);
					expect(selections).toBe(before);
					expect(readFileSync(marker, "utf8")).toBe("");
				}
				for (const value of [...dangerous, "git push", "git push>/dev/null", "git push 2>/dev/null", "fixture-read 'sudo hook-veto'"]) {
					const before = selections;
					await run(value, true);
					expect(selections).toBe(before + (hasUI && dangerous.includes(value) ? 1 : 0));
					expect(readFileSync(marker, "utf8")).toBe("");
				}
				await run("sudo approved", false);
				expect(readFileSync(marker, "utf8")).toBe("fixture\n");
				if (hasUI) {
					answer = "Yes";
					const before = selections;
					await run("sudo confirmed", false);
					expect(selections).toBe(before + 1);
					expect(readFileSync(marker, "utf8")).toBe("fixture\nfixture\n");
				}
				expect(calls.some((call) => call.name === "bash" && (nested ? !!call.parent : !call.parent))).toBe(true);
				expect(network).not.toHaveBeenCalled();
			} finally {
				session?.dispose();
				network.mockRestore();
				rmSync(root, { recursive: true, force: true });
			}
		},
		30000,
	);
});
