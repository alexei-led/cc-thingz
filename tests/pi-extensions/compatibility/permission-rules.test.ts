import { afterAll, afterEach, describe, expect, it, mock } from "bun:test";
import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from "node:fs";
import { homedir, tmpdir } from "node:os";
import { join, relative } from "node:path";

const { default: permissionGate } = await import("../../../src/plugins/pi/extensions/extensions/permission-gate.ts");
const root = mkdtempSync(join(tmpdir(), "permission-rules-"));
const user = join(root, "user");
const project = join(root, "project");
const oldAgentDir = process.env.PI_CODING_AGENT_DIR;
mkdirSync(user, { recursive: true });
mkdirSync(join(project, ".pi"), { recursive: true });
process.env.PI_CODING_AGENT_DIR = user;

afterAll(() => {
	if (oldAgentDir === undefined) delete process.env.PI_CODING_AGENT_DIR;
	else process.env.PI_CODING_AGENT_DIR = oldAgentDir;
	rmSync(root, { recursive: true, force: true });
});
afterEach(() => {
	rmSync(join(user, "settings.json"), { force: true });
	rmSync(join(project, ".pi", "settings.json"), { force: true });
});

async function setup(
	userConfig: unknown,
	projectConfig: unknown,
	trusted = true,
	options: {
		hasUI?: boolean;
		choice?: string;
		responder?: (payload: any) => void;
		notify?: (message: string, level?: string) => void;
	} = {},
) {
	if (userConfig !== undefined) writeFileSync(join(user, "settings.json"), JSON.stringify(userConfig));
	if (projectConfig !== undefined) writeFileSync(join(project, ".pi", "settings.json"), JSON.stringify(projectConfig));
	const handlers = new Map<string, Function>();
	permissionGate({
		on: (name: string, handler: Function) => handlers.set(name, handler),
		registerCommand: () => {},
		events: { emit: (_name: string, payload: any) => (options.responder ? options.responder(payload) : payload.onResult?.({})) },
	} as any);
	const ctx = {
		cwd: project,
		isProjectTrusted: () => trusted,
		hasUI: options.hasUI ?? false,
		sessionManager: { getSessionId: () => "s" },
		ui: { select: mock(async () => options.choice ?? "No"), notify: options.notify ?? mock() },
	};
	await handlers.get("session_start")!({}, ctx);
	return (command: string) => handlers.get("tool_call")!({ toolName: "bash", input: { command } }, ctx);
}

const ssh = "gcloud compute ssh reflex-kroo-01 --zone us-central1-a --project doit-reflex --quiet --command";
const sshGrant = { match: `Bash(${ssh} *)`, headless: true };
const localGrant = { match: "Bash(sudo whoami)", headless: true };
const gitDeny = { match: "Bash(git push)" };
const policies = [
	["none", undefined, undefined],
	["user grant", { permissionGate: { allow: [sshGrant] } }, undefined],
	["project grant", undefined, { permissionGate: { allow: [sshGrant] } }],
	["unrelated deny", { permissionGate: { deny: [gitDeny] } }, { permissionGate: { allow: [sshGrant] } }],
] as const;

const developerCommands = [
	"sed -n 1,120p tools/core/_finding_spend.py; echo '=====ESTIMATE'; sed -n 1,140p tools/core/_facts_finding_estimate.py",
	"rg -n 'def compute_estimate|def .*estimate' tools/core/_finding_estimate.py | head -30",
	"rg -n 'set-finding-estimate|set_finding_estimate|refresh-finding-estimate|finding-estimate' --glob '!node_modules' --glob '!.gitnexus' . | head -40; echo '=== candidate-pricing job'; ls setup/cron/jobs/*/ | head -80",
	"rg -rn --no-heading 'REFLEX_CANDIDATE_PRICING' setup/layers setup/files/skills setup/files/agent-skills setup/cron tools/core/_lib.py 2>/dev/null | cut -c1-200",
	"ls ~/Workspace | head -20; echo '=== customers repo'; ls ~/Workspace/reflex-customers 2>/dev/null | head; echo '=== gcloud'; which gcloud; echo '=== instances'; cat setup/fleet.tsv 2>/dev/null | head -20",
	`${ssh} 'sudo -i -u reflex\nreflex-aws-capability-matrix --help' 2>&1 | tail -35`,
	`${ssh} 'sudo whoami' | grep -v 'WARNING' | tail -35 | wc -l`,
	"cd /tmp && uv run --no-project python - <<'PY'\nfrom pathlib import Path\ns = 'sudo rm -rf /example'\nprint(s)\nPY\nmake fmt && make build && bun test",
	"python -c 'print(\"sudo\")'",
	"node -e 'console.log(\"rm -rf /example\")'",
	"bash -c 'printf ok'",
	"printf '%s' 'sudo' | awk '{print $1}'",
	"rg pattern . | sort -u | uniq -c | head -50",
	"rg pattern . > results.txt",
	"some-developer-tool --flag value && another-tool",
	"gcloud compute ssh another --project another --command 'hostname'",
	"cd /tmp && timeout 5 gcloud version",
	"/usr/bin/gcloud version; true",
	"env -u HOME gcloud version",
	"echo ok # sudo is just a comment",
	"find . -name 'sudo' -print",
	'printf "%s" "$(rg -F sudo README.md | head -1)"',
	'printf "%s" "$(node -e \'console.log(\\"sudo\\")\')" current',
	"printf '%s' `printf sudo`",
	'printf "%s" "${name:-sudo}"',
	'printf "%s" "${#sudo}"',
	"python - <<P\"Y\"\ntext = 'sudo'\nPY",
	"cat <<''\nsudo is data\n\necho done",
	"node - <<<'console.log(\"sudo\")'",
	"python - <<\\PY\ntext = 'sudo'\nPY",
	"python - <<-'PY'\n\ttext = 'sudo'\n\tPY",
	"find . -name 'sudo' -exec echo {} +",
	"timeout 5 python -c 'print(\"sudo\")'",
	"printf '%s' 'sudo' | xargs -0 grep sudo",
];

describe.each(policies)("blacklist defaults: %s", (_name, userConfig, projectConfig) => {
	it.each(developerCommands)("does not gate normal developer work: %s", async (command) => {
		for (const hasUI of [false, true]) {
			const run = await setup(userConfig, projectConfig, true, { hasUI, choice: "No" });
			expect(await run(command)).toBeUndefined();
		}
	});
});

describe("real Bash developer-flow smoke", () => {
	it("runs the five reported read-only flows against isolated fixtures", async () => {
		const { createBashToolDefinition } = await import("@earendil-works/pi-coding-agent");
		for (const dir of ["tools/core", "setup/layers", "setup/files/skills", "setup/files/agent-skills", "setup/cron/jobs/example"])
			mkdirSync(join(project, dir), { recursive: true });
		mkdirSync(join(root, "Workspace/reflex-customers"), { recursive: true });
		for (const file of ["_finding_spend.py", "_facts_finding_estimate.py", "_finding_estimate.py", "_lib.py"])
			writeFileSync(join(project, "tools/core", file), "def compute_estimate(): pass\n# REFLEX_CANDIDATE_PRICING set-finding-estimate\n");
		writeFileSync(join(project, "setup/fleet.tsv"), "fixture\tzone\n");
		const run = await setup({ permissionGate: { deny: [gitDeny] } }, { permissionGate: { allow: [sshGrant] } });
		const bash = createBashToolDefinition(project, {
			exposeSessionEnvironment: false,
			spawnHook: (context) => ({ ...context, env: { ...context.env, HOME: root } }),
		});
		for (const command of developerCommands.slice(0, 5)) {
			expect(await run(command)).toBeUndefined();
			const result = await bash.execute("read-only-smoke", { command, timeout: 10 }, new AbortController().signal, undefined, { cwd: project } as any);
			expect(result.isError).not.toBe(true);
			expect(result.structuredContent).toMatchObject({ exit_code: 0 });
		}
	});
});

describe("permission exceptions and explicit denies", () => {
	it("preserves explicit denies for terminal tools", async () => {
		const run = await setup({ permissionGate: { deny: [{ match: "Bash(herdr agent prompt worker *)" }] } }, undefined);
		expect(await run("herdr agent prompt worker 'hello'")).toEqual({ block: true, reason: "Blocked by user permission rule" });
	});
	it("allows an exact eligible exception to a built-in warning", async () => {
		const run = await setup({ permissionGate: { allow: [localGrant] } }, undefined);
		expect(await run("sudo whoami")).toBeUndefined();
		expect(await run("sudo hostname")).toMatchObject({ block: true });
	});
	it.each(["sudo whoami; echo ok", "sudo whoami | tail -35", "sudo $(echo whoami)", "env sudo whoami"])(
		"does not extend an exception to an undescribed dangerous invocation: %s",
		async (command) => {
			const run = await setup({ permissionGate: { allow: [localGrant] } }, undefined);
			expect(await run(command)).toMatchObject({ block: true });
		},
	);
	it("requires headless eligibility for warning exceptions", async () => {
		const run = await setup({ permissionGate: { allow: [{ match: localGrant.match }] } }, undefined);
		expect(await run("sudo whoami")).toMatchObject({ block: true });
	});
	it("accepts any matching eligible headless grant", async () => {
		const run = await setup({ permissionGate: { allow: [{ match: "Bash(sudo *)" }] } }, { permissionGate: { allow: [localGrant] } });
		expect(await run("sudo whoami")).toBeUndefined();
	});
	it("requires project trust before applying a warning exception", async () => {
		const run = await setup(undefined, { permissionGate: { allow: [localGrant] } }, false);
		expect(await run("sudo whoami")).toMatchObject({ block: true });
	});
	it("allows trusted project exceptions", async () => {
		const run = await setup(undefined, { permissionGate: { allow: [localGrant] } });
		expect(await run("sudo whoami")).toBeUndefined();
	});
	it.each([
		"git push",
		"echo ok; git push",
		"printf ok | git push",
		"env git push",
		"timeout 5 git push",
		"git push>/dev/null",
		"git push 2>/dev/null",
		"git push >out",
		'echo "$(git push)"',
		"cat <<END\n$(git push)\nEND",
	])("denies a positively matched invocation: %s", async (command) => {
		const run = await setup({ permissionGate: { deny: [gitDeny] } }, undefined, true, { hasUI: true, choice: "Yes" });
		expect(await run(command)).toEqual({ block: true, reason: "Blocked by user permission rule" });
	});
	it("does not strip literal redirection characters from deny arguments", async () => {
		const run = await setup({ permissionGate: { deny: [{ match: "Bash(printf)" }] } }, undefined);
		expect(await run("printf '>'")).toBeUndefined();
		expect(await run("printf '<'")).toBeUndefined();
	});
	it("does not match a deny inside quoted source", async () => {
		const run = await setup({ permissionGate: { deny: [gitDeny] } }, undefined);
		expect(await run("python -c 'print(\"git push\")'")).toBeUndefined();
	});
	it("preserves user deny precedence over project allow", async () => {
		const run = await setup({ permissionGate: { deny: [{ match: localGrant.match }] } }, { permissionGate: { allow: [localGrant] } });
		expect(await run("sudo whoami")).toEqual({ block: true, reason: "Blocked by user permission rule" });
	});
	it("emits PermissionDenied for rule denials", async () => {
		const events: string[] = [];
		const run = await setup({ permissionGate: { deny: [gitDeny] } }, undefined, true, {
			responder: (payload) => {
				events.push(payload.hookEventName);
				payload.onResult({});
			},
		});
		expect(await run("git push")).toMatchObject({ block: true });
		expect(events).toEqual(["PermissionDenied"]);
	});
	it("keeps a hook veto on a normally allowed developer pipeline", async () => {
		const events: string[] = [];
		const run = await setup(undefined, undefined, true, {
			responder: (payload) => {
				events.push(payload.hookEventName);
				payload.onResult(payload.hookEventName === "PermissionRequest" ? { behavior: "deny", reason: "hook policy" } : {});
			},
		});
		expect(await run("rg 'sudo' . | head -30")).toEqual({ block: true, reason: "hook policy" });
		expect(events).toEqual(["PermissionRequest", "PermissionDenied"]);
	});
	it.each(["git push", "echo ok; git push", "sudo hostname", ""])("rejects unsafe hook replacements: %s", async (patch) => {
		const run = await setup({ permissionGate: { deny: [gitDeny] } }, undefined, true, {
			responder: (payload) => payload.onResult(payload.hookEventName === "PermissionRequest" ? { behavior: "allow", updatedInput: { command: patch } } : {}),
		});
		expect(await run("sudo whoami")).toMatchObject({ block: true, reason: "PermissionRequest hook returned an unsafe command patch" });
	});
	it("accepts harmless compound hook replacements", async () => {
		const run = await setup({ permissionGate: { allow: [localGrant] } }, undefined, true, {
			responder: (payload) =>
				payload.onResult(payload.hookEventName === "PermissionRequest" ? { behavior: "allow", updatedInput: { command: "echo ok; pwd" } } : {}),
		});
		expect(await run("sudo whoami")).toBeUndefined();
	});
	it("accepts BOM-prefixed settings", async () => {
		writeFileSync(join(user, "settings.json"), "\ufeff" + JSON.stringify({ permissionGate: { allow: [localGrant] } }));
		const run = await setup(undefined, undefined);
		expect(await run("sudo whoami")).toBeUndefined();
	});
	it("uses Pi's tilde expansion for its settings directory", async () => {
		writeFileSync(join(user, "settings.json"), JSON.stringify({ permissionGate: { allow: [localGrant] } }));
		process.env.PI_CODING_AGENT_DIR = `~/${relative(homedir(), user)}`;
		try {
			expect(await (await setup(undefined, undefined))("sudo whoami")).toBeUndefined();
		} finally {
			process.env.PI_CODING_AGENT_DIR = user;
		}
	});
	it("reports invalid user policy at startup", async () => {
		const notify = mock();
		const run = await setup({ permissionGate: { deny: "bad" } }, undefined, true, { hasUI: true, notify });
		expect(notify).toHaveBeenCalledWith(expect.stringContaining("Invalid user permission policy"), "error");
		expect(await run("echo ok")).toMatchObject({ block: true });
	});
});
