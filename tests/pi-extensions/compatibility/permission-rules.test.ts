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

const prefix = "gcloud compute ssh reflex-kroo-01 --zone us-central1-a --project doit-reflex --quiet --command";
const grant = { match: `Bash(${prefix} *)`, headless: true };

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

describe("permission rules", () => {
	it("allows literal remote payloads for the exact VM", async () => {
		const run = await setup({ permissionGate: { allow: [grant] } }, undefined);
		expect(await run(`${prefix} 'sudo systemctl restart reflex'`)).toBeUndefined();
		expect(await run(`${prefix} 'sudo whoami; echo ok'`)).toBeUndefined();
	});
	it.each([
		`${prefix} "$(sudo whoami)"`,
		`${prefix} 'sudo whoami'; echo x`,
		`${prefix} x;whoami`,
		`${prefix} x|sh`,
		`${prefix} x&&whoami`,
		`${prefix} x>out`,
		`${prefix} 'sudo whoami' && whoami`,
		`${prefix} 'sudo whoami' > out`,
		`${prefix} \`sudo whoami\``,
		`${prefix} $'sudo whoami'`,
		`${prefix} 'sudo whoami'\nwhoami`,
	])("blocks shell syntax outside the rule: %s", async (command) => {
		const run = await setup({ permissionGate: { allow: [grant] } }, undefined);
		expect(await run(command)).toMatchObject({ block: true });
	});
	it("allows a permitted SSH command piped to a bounded local tail", async () => {
		const run = await setup({ permissionGate: { allow: [grant] } }, undefined);
		expect(await run(`${prefix} 'sudo -i -u reflex\nreflex-aws-capability-matrix --help' 2>&1 | tail -35`)).toBeUndefined();
	});
	it("allows the project wildcard-instance rule with the reported pipeline", async () => {
		const wildcard = { match: "Bash(gcloud compute ssh * --zone us-central1-a --project doit-reflex --quiet --command *)", headless: true };
		const run = await setup(undefined, { permissionGate: { allow: [wildcard] } });
		expect(await run(`${prefix} 'sudo -i -u reflex\nreflex-aws-capability-matrix --help' 2>&1 | tail -35`)).toBeUndefined();
	});
	it.each(["| tail", "| head -35", "2>&1 | tail -n 35", "| head -n 0"])("allows a safe output filter: %s", async (suffix) => {
		const run = await setup({ permissionGate: { allow: [grant] } }, undefined);
		expect(await run(`${prefix} 'sudo whoami' ${suffix}`)).toBeUndefined();
	});
	it.each([
		"| tail -f",
		"| tail /etc/passwd",
		"| tail -35 /etc/passwd",
		"| tail -10001",
		"| tail -35 > out",
		"| tail -35; whoami",
		"| tail -35 | sh",
		"| tail -n $(whoami)",
		"> out | tail -35",
		"2>out | tail -35",
	])("blocks unsafe output syntax: %s", async (suffix) => {
		const run = await setup({ permissionGate: { allow: [grant] } }, undefined);
		expect(await run(`${prefix} 'sudo whoami' ${suffix}`)).toMatchObject({ block: true });
	});
	it.each(["Bash(tail -35)", "Bash(tail *)"])("honors an output filter deny: %s", async (pattern) => {
		const run = await setup({ permissionGate: { allow: [grant], deny: [{ match: pattern }] } }, undefined);
		expect(await run(`${prefix} 'sudo whoami' 2>&1 | tail -35`)).toMatchObject({ block: true, reason: "Blocked by user permission rule" });
	});
	it("does not authorize an unmatched command with a safe output filter", async () => {
		const run = await setup({ permissionGate: { allow: [grant] } }, undefined);
		expect(await run(`${prefix.replace("reflex-kroo-01", "other")} 'sudo whoami' | tail -35`)).toMatchObject({ block: true });
	});
	it("keeps hook denies for a permitted pipeline", async () => {
		const run = await setup({ permissionGate: { allow: [grant] } }, undefined, true, {
			responder: (payload) => payload.onResult(payload.hookEventName === "PermissionRequest" ? { behavior: "deny", reason: "hook denied" } : {}),
		});
		expect(await run(`${prefix} 'sudo whoami' | tail -35`)).toEqual({ block: true, reason: "hook denied" });
	});
	it("allows a chain of read-only stdin filters", async () => {
		const run = await setup({ permissionGate: { allow: [grant] } }, undefined);
		expect(await run(`${prefix} 'sudo whoami' 2>&1 | grep -v 'WARNING' | tail -35 | wc -l`)).toBeUndefined();
	});
	it.each(["| cat", "| grep -v 'WARNING'", "| grep -E -i 'warn|error'", "| wc -l"])("allows read-only stdin filters: %s", async (suffix) => {
		const run = await setup({ permissionGate: { allow: [grant] } }, undefined);
		expect(await run(`${prefix} 'sudo whoami' ${suffix}`)).toBeUndefined();
	});
	it.each([
		"| grep -f /etc/passwd",
		"| grep foo /etc/passwd",
		"| grep --include=x foo",
		"| wc /etc/passwd",
		"| cat /etc/passwd",
		"| grep $(whoami)",
		"| sh",
		"| grep -v x >out",
	])("blocks unapproved filter behavior: %s", async (suffix) => {
		const run = await setup({ permissionGate: { allow: [grant] } }, undefined);
		expect(await run(`${prefix} 'sudo whoami' ${suffix}`)).toMatchObject({ block: true });
	});
	it("does not compose arbitrary allow rules into pipeline approval", async () => {
		const sort = { match: "Bash(sort -u)", headless: true };
		const run = await setup({ permissionGate: { allow: [grant, sort] } }, undefined);
		expect(await run(`${prefix} 'sudo whoami' | sort -u | head -10`)).toMatchObject({ block: true });
		const denied = await setup({ permissionGate: { allow: [grant, sort], deny: [{ match: sort.match }] } }, undefined);
		expect(await denied(`${prefix} 'sudo whoami' | sort -u`)).toMatchObject({ block: true, reason: "Blocked by user permission rule" });
	});
	it("requires headless approval for explicitly permitted pipeline stages", async () => {
		const run = await setup({ permissionGate: { allow: [grant, { match: "Bash(sort -u)" }] } }, undefined);
		expect(await run(`${prefix} 'sudo whoami' | sort -u`)).toMatchObject({ block: true });
	});
	it("does not allow a different target or extra flag", async () => {
		const run = await setup({ permissionGate: { allow: [grant] } }, undefined);
		expect(await run(`${prefix.replace("reflex-kroo-01", "other")} 'sudo whoami'`)).toMatchObject({ block: true });
		expect(await run(`${prefix} 'sudo whoami' --ssh-flag=x`)).toMatchObject({ block: true });
		expect(await run(`${prefix} 'whoami' --ssh-flag=-V`)).toMatchObject({ block: true });
		expect(await run(`${prefix.replace("reflex-kroo-01", "other")} 'whoami'`)).toMatchObject({ block: true });
		expect(await run(`${prefix} 'whoami'\${IFS}--ssh-flag=-V`)).toMatchObject({ block: true });
	});
	it("honors project trust and user deny precedence", async () => {
		const command = `${prefix} 'sudo whoami'`;
		expect(await (await setup(undefined, { permissionGate: { allow: [{ match: "Bash(sudo whoami)", headless: true }] } }, false))("sudo whoami")).toMatchObject(
			{ block: true },
		);
		expect(await (await setup({ permissionGate: { deny: [grant] } }, { permissionGate: { allow: [grant] } }))(command)).toMatchObject({
			block: true,
			reason: "Blocked by user permission rule",
		});
	});
	it("cannot bypass a user deny with opaque shell syntax", async () => {
		const run = await setup({ permissionGate: { deny: [{ match: "Bash(sudo *)" }] } }, undefined, true, { hasUI: true, choice: "Yes" });
		expect(await run("echo ok; sudo whoami")).toMatchObject({ block: true, reason: "Unrecognized shell syntax cannot be checked against deny rules" });
	});
	it("honors hook denial on unrecognized shell syntax before prompting", async () => {
		const events: string[] = [];
		const run = await setup({ permissionGate: { allow: [grant] } }, undefined, true, {
			hasUI: true,
			choice: "Yes",
			responder: (payload) => {
				events.push(payload.hookEventName);
				payload.onResult(payload.hookEventName === "PermissionRequest" ? { behavior: "deny", reason: "hook denied" } : {});
			},
		});
		expect(await run("sudo whoami | cat")).toEqual({ block: true, reason: "hook denied" });
		expect(events).toEqual(["PermissionRequest", "PermissionDenied"]);
	});
	it.each([
		[{ deny: [{ match: "Bash(git push)" }] }, "git push"],
		[{ allow: [grant] }, "echo ok; git push"],
	])("rejects hook patches that violate configured rules", async (permissionGate, patch) => {
		const run = await setup({ permissionGate }, undefined, true, {
			responder: (payload) => payload.onResult(payload.hookEventName === "PermissionRequest" ? { behavior: "allow", updatedInput: { command: patch } } : {}),
		});
		expect(await run("sudo whoami")).toEqual({ block: true, reason: "PermissionRequest hook returned an unsafe command patch" });
	});
	it("notifies at session start when user rules are invalid", async () => {
		const notify = mock();
		await setup({ permissionGate: { deny: "bad" } }, undefined, true, { hasUI: true, notify });
		expect(notify).toHaveBeenCalledWith(expect.stringContaining("Invalid user permission policy"), "error");
	});
	it("notifies hooks when rules deny", async () => {
		const events: string[] = [];
		const run = await setup({ permissionGate: { deny: [{ match: "Bash(sudo *)" }] } }, undefined, true, {
			responder: (payload) => {
				events.push(payload.hookEventName);
				payload.onResult({});
			},
		});
		expect(await run("sudo whoami")).toMatchObject({ block: true });
		expect(events).toEqual(["PermissionDenied"]);
	});
	it("accepts a BOM in user settings", async () => {
		writeFileSync(join(user, "settings.json"), "\ufeff" + JSON.stringify({ permissionGate: { allow: [grant] } }));
		const withBom = await setup(undefined, undefined);
		expect(await withBom(`${prefix} 'sudo whoami'`)).toBeUndefined();
	});
	it("resolves a tilde-prefixed agent directory using Pi path rules", async () => {
		writeFileSync(join(user, "settings.json"), JSON.stringify({ permissionGate: { allow: [grant] } }));
		process.env.PI_CODING_AGENT_DIR = `~/${relative(homedir(), user)}`;
		try {
			const run = await setup(undefined, undefined);
			expect(await run(`${prefix} 'sudo whoami'`)).toBeUndefined();
		} finally {
			process.env.PI_CODING_AGENT_DIR = user;
		}
	});
	it("allows trusted project rules", async () => {
		const run = await setup(undefined, { permissionGate: { allow: [grant] } });
		expect(await run(`${prefix} 'sudo whoami'`)).toBeUndefined();
	});
	it("does not let SSH grants obstruct unrelated inspection pipelines", async () => {
		const run = await setup(undefined, { permissionGate: { allow: [grant] } });
		expect(await run("rg -F 'sudo' README.md | head -20")).toBeUndefined();
	});
	it("does not let SSH grants obstruct unrelated developer scripts", async () => {
		const run = await setup(undefined, { permissionGate: { allow: [grant] } });
		const command =
			"cd /tmp && uv run --no-project python - <<'PY'\nfrom pathlib import Path\np = Path('notes.md')\ns = 'sudo -i -u reflex'\np.write_text(s)\nPY\nmake fmt && make build && bun test";
		expect(await run(command)).toBeUndefined();
	});
	it("fails closed on invalid user policy", async () => {
		const run = await setup({ permissionGate: { deny: "bad" } }, undefined);
		expect(await run("echo ok")).toMatchObject({ block: true });
	});
	it("requires explicit headless permission", async () => {
		const run = await setup({ permissionGate: { allow: [{ match: grant.match }] } }, undefined);
		expect(await run(`${prefix} 'sudo whoami'`)).toMatchObject({ block: true });
	});
});
