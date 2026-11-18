import { afterAll, afterEach, describe, expect, it, mock } from "bun:test";
import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

mock.module("@earendil-works/pi-coding-agent", () => ({}));

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

async function setup(userConfig: unknown, projectConfig: unknown, trusted = true) {
	if (userConfig !== undefined) writeFileSync(join(user, "settings.json"), JSON.stringify(userConfig));
	if (projectConfig !== undefined) writeFileSync(join(project, ".pi", "settings.json"), JSON.stringify(projectConfig));
	const handlers = new Map<string, Function>();
	permissionGate({
		on: (name: string, handler: Function) => handlers.set(name, handler),
		registerCommand: () => {},
		events: { emit: (_name: string, payload: any) => payload.onResult?.({}) },
	} as any);
	const ctx = {
		cwd: project,
		isProjectTrusted: () => trusted,
		hasUI: false,
		sessionManager: { getSessionId: () => "s" },
		ui: { select: mock(async () => "No") },
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
		`${prefix} 'sudo whoami' | cat`,
		`${prefix} 'sudo whoami' && whoami`,
		`${prefix} 'sudo whoami' > out`,
		`${prefix} \`sudo whoami\``,
		`${prefix} $'sudo whoami'`,
		`${prefix} 'sudo whoami'\nwhoami`,
	])("blocks shell syntax outside the rule: %s", async (command) => {
		const run = await setup({ permissionGate: { allow: [grant] } }, undefined);
		expect(await run(command)).toMatchObject({ block: true });
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
		expect(await (await setup(undefined, { permissionGate: { allow: [grant] } }, false))(command)).toMatchObject({ block: true });
		expect(await (await setup({ permissionGate: { deny: [grant] } }, { permissionGate: { allow: [grant] } }))(command)).toMatchObject({
			block: true,
			reason: "Blocked by user permission rule",
		});
	});
	it("cannot bypass a user deny with opaque shell syntax", async () => {
		const run = await setup({ permissionGate: { deny: [{ match: "Bash(sudo *)" }] } }, undefined);
		expect(await run("echo ok; sudo whoami")).toMatchObject({ block: true });
	});
	it("allows trusted project rules", async () => {
		const run = await setup(undefined, { permissionGate: { allow: [grant] } });
		expect(await run(`${prefix} 'sudo whoami'`)).toBeUndefined();
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
