import { readFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

export type Rule = { match: string; headless: boolean; words: string[]; source: "user" | "project" };
export type Policy = { allow: Rule[]; deny: Rule[]; error?: string; warning?: string };

function parseRule(value: unknown, source: "user" | "project"): Rule {
	if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("rule must be an object");
	const rule = value as Record<string, unknown>;
	if (typeof rule.match !== "string" || !/^Bash\([^()\n]+\)$/.test(rule.match)) throw new Error("rule must use Bash(words)");
	if (rule.headless !== undefined && typeof rule.headless !== "boolean") throw new Error("headless must be boolean");
	const words = rule.match.slice(5, -1).split(" ");
	if (!words.length || words.some((word) => !word || !/^(?:\*|[a-zA-Z0-9_./:@%+=,-]+)$/.test(word)) || words[0] === "*")
		throw new Error("rule contains an invalid word");
	return { match: rule.match, headless: rule.headless === true, words, source };
}

function readPolicy(path: string, project: boolean): Policy {
	let input: string;
	try {
		input = readFileSync(path, "utf8");
	} catch (error) {
		if ((error as NodeJS.ErrnoException).code === "ENOENT") return { allow: [], deny: [] };
		throw error;
	}
	const settings: unknown = JSON.parse(input);
	if (!settings || typeof settings !== "object" || Array.isArray(settings)) throw new Error("settings must be an object");
	const gate = (settings as Record<string, unknown>).permissionGate;
	if (gate === undefined) return { allow: [], deny: [] };
	if (!gate || typeof gate !== "object" || Array.isArray(gate)) throw new Error("permissionGate must be an object");
	const config = gate as Record<string, unknown>;
	if (project && config.deny !== undefined) throw new Error("project deny rules are not supported");
	if (config.allow !== undefined && !Array.isArray(config.allow)) throw new Error("allow must be an array");
	if (config.deny !== undefined && !Array.isArray(config.deny)) throw new Error("deny must be an array");
	return {
		allow: Array.isArray(config.allow) ? config.allow.map((value) => parseRule(value, project ? "project" : "user")) : [],
		deny: Array.isArray(config.deny) ? config.deny.map((value) => parseRule(value, "user")) : [],
	};
}

export function loadPolicy(cwd: string, trusted: boolean): Policy {
	const agentDir = process.env.PI_CODING_AGENT_DIR || join(homedir(), ".pi", "agent");
	let user: Policy;
	try {
		user = readPolicy(join(agentDir, "settings.json"), false);
	} catch (error) {
		return { allow: [], deny: [], error: `Invalid user permission policy: ${String(error)}` };
	}
	if (!trusted) return user;
	try {
		const project = readPolicy(join(cwd, ".pi", "settings.json"), true);
		return { allow: [...user.allow, ...project.allow], deny: user.deny };
	} catch (error) {
		return { ...user, warning: `Invalid project permission policy ignored: ${String(error)}` };
	}
}

export function parseLiteralCommand(command: string): string[] | undefined {
	const words: string[] = [];
	let word = "";
	let active = false;
	let quote: "'" | '"' | undefined;
	for (let i = 0; i < command.length; i++) {
		const c = command[i];
		if (quote === "'") {
			if (c === "'") quote = undefined;
			else word += c;
			continue;
		}
		if (quote === '"') {
			if (c === '"') quote = undefined;
			else if (c === "$" || c === "`" || c === "\\") return undefined;
			else word += c;
			continue;
		}
		if (c === "'" || c === '"') {
			quote = c;
			active = true;
		} else if (c === "\\") {
			const next = command[++i];
			if (next === "\n") continue;
			if (next !== "'") return undefined;
			word += next;
			active = true;
		} else if (c === " " || c === "\t") {
			if (active) words.push(word);
			word = "";
			active = false;
		} else if (/[a-zA-Z0-9_./:@%+=,-]/.test(c)) {
			word += c;
			active = true;
		} else {
			return undefined;
		}
	}
	if (quote) return undefined;
	if (active) words.push(word);
	if (!words.length || !words[0] || words[0].includes("=")) return undefined;
	return words;
}

export function matchesRule(rule: Rule, words: string[]): boolean {
	return rule.words.length === words.length && rule.words.every((word, i) => (word === "*" ? !!words[i] && !words[i].startsWith("-") : word === words[i]));
}
