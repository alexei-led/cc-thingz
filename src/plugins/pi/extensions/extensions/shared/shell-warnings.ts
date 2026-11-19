import { basename } from "node:path";
import { fileURLToPath } from "node:url";
import { Language, Parser, type Node } from "web-tree-sitter";
import { parseLiteralCommand } from "./literal-command.js";

const recursiveRm = /\brm\s+(?:(?:-[a-zA-Z]+|--[a-z]+(?:-[a-z]+)*)\s+)*(?:-[a-zA-Z]*[rR][a-zA-Z]*|--recursive)(?=\s|$)/;
const rawPatterns = [recursiveRm, /\bsudo\b/i, /\b(chmod|chown)\b.*777/i];
const MAX_COMMAND_BYTES = 256 * 1024;
const MAX_PARSE_MS = 50;
const MAX_NODES = 100_000;
const MAX_RUNNER_DEPTH = 32;
const runnerValueFlags: Record<string, readonly string[]> = {
	time: ["-f", "-o", "--format", "--output"],
	nohup: [],
	timeout: ["-s", "--signal", "-k", "--kill-after"],
	nice: ["-n", "--adjustment"],
	stdbuf: ["-i", "-o", "-e", "--input", "--output", "--error"],
	ionice: ["-c", "-n", "-p", "-P", "-u", "--class", "--classdata", "--pid", "--pgid", "--uid"],
	xargs: [
		"-n",
		"-P",
		"-L",
		"-s",
		"-E",
		"-I",
		"-a",
		"-d",
		"--arg-file",
		"--delimiter",
		"--max-args",
		"--max-procs",
		"--max-lines",
		"--max-chars",
		"--eof",
		"--replace",
	],
};

await Parser.init();
const language = await Language.load(fileURLToPath(new URL("./tree-sitter-bash.wasm", import.meta.url)));
const parser = new Parser().setLanguage(language);

type Inspection = { dangerous: boolean; commands: string[][] };
type Words = Array<string | undefined>;

export function hasWarningText(command: string): boolean {
	return rawPatterns.some((pattern) => pattern.test(command));
}

function literal(node: Node): string | undefined {
	if (node.hasError || node.isMissing || !["command_name", "word", "number", "raw_string", "string", "concatenation"].includes(node.type)) return undefined;
	const text =
		node.type === "word" || node.type === "command_name" || (node.type === "concatenation" && !/['"`$]/.test(node.text))
			? node.text.replace(/\\([a-zA-Z0-9_./:@%+=,{};-])/g, "$1").replace(/[{};]/g, (c) => `'${c}'`)
			: node.text;
	const words = parseLiteralCommand("argument " + text);
	return words?.length === 2 ? words[1] : undefined;
}

function record(words: Words, result: Inspection): void {
	const values = words.filter((word): word is string => word !== undefined);
	if (values.length === words.length && values.length > 0) result.commands.push(values);
}

function inspectInvocation(words: Words, result: Inspection, depth = 0): void {
	if (depth >= MAX_RUNNER_DEPTH) return;
	record(words, result);
	let i = 0;
	while (i < words.length) {
		const word = words[i];
		if (word === undefined) return;
		if (/^[a-zA-Z_][a-zA-Z0-9_]*=/.test(word)) {
			i++;
			continue;
		}
		const wrapper = basename(word);
		if (wrapper === "env") {
			i++;
			while (i < words.length && words[i]?.startsWith("-")) {
				const attached = words[i]?.startsWith("--split-string=");
				if (words[i] === "-S" || words[i] === "--split-string" || attached) {
					const source = attached ? words[i]?.slice("--split-string=".length) : words[i + 1];
					const split = source === undefined ? undefined : parseLiteralCommand(`env ${source}`)?.slice(1);
					if (split) inspectInvocation(["env", ...split, ...words.slice(i + (attached ? 1 : 2))], result, depth + 1);
					return;
				}
				i += ["-u", "--unset", "-C", "--chdir", "-a", "--argv0", "-P"].includes(words[i] ?? "") ? 2 : 1;
			}
			continue;
		}
		if (wrapper === "command" || wrapper === "exec") {
			i++;
			while (i < words.length) {
				if (wrapper === "exec" && words[i] === "-a") {
					i += 2;
					continue;
				}
				if (words[i] === "--" || (wrapper === "command" ? words[i] === "-p" : ["-c", "-l"].includes(words[i] ?? ""))) {
					i++;
					continue;
				}
				break;
			}
			continue;
		}
		if (Object.hasOwn(runnerValueFlags, wrapper)) {
			i++;
			while (i < words.length && words[i]?.startsWith("-")) {
				if (words[i] === "--") {
					i++;
					break;
				}
				i += runnerValueFlags[wrapper].includes(words[i] ?? "") ? 2 : 1;
			}
			if (wrapper === "timeout") i++;
			continue;
		}
		break;
	}
	const executable = words[i];
	if (executable === undefined) return;
	if (i > 0) record(words.slice(i), result);
	const name = basename(executable);
	const args = words.slice(i + 1);
	if (name === "find") {
		for (let j = 0; j < args.length; j++) {
			if (!["-exec", "-execdir", "-ok", "-okdir"].includes(args[j] ?? "")) continue;
			let end = j + 1;
			while (end < args.length && args[end] !== ";" && args[end] !== "+") end++;
			inspectInvocation(args.slice(j + 1, end), result, depth + 1);
			j = end;
		}
	}
	const options = args.slice(0, args.includes("--") ? args.indexOf("--") : undefined);
	const mode = args.find((arg) => arg === undefined || !arg.startsWith("-"));
	const referenceMode = args.some((arg) => arg === "--reference" || arg?.startsWith("--reference="));
	if (
		name === "sudo" ||
		(name === "rm" && options.some((arg) => arg === "--recursive" || (arg !== undefined && /^-[a-zA-Z]+$/.test(arg) && /[rR]/.test(arg)))) ||
		((name === "chmod" || name === "chown") && !referenceMode && mode !== undefined && /^[0-7]?777$/.test(mode))
	)
		result.dangerous = true;
}

// Syntax recognition is best-effort and bounded; unknown input is not an automatic denial.
// This is never used to grant an exception: only the strict literal parser does that.
export function inspectShellWarnings(command: string): Inspection {
	const result: Inspection = { dangerous: false, commands: [] };
	if (Buffer.byteLength(command, "utf8") > MAX_COMMAND_BYTES) return { dangerous: hasWarningText(command), commands: [] };
	let tree;
	try {
		const deadline = performance.now() + MAX_PARSE_MS;
		tree = parser.parse(command, null, { progressCallback: () => performance.now() >= deadline });
		if (!tree) return { dangerous: hasWarningText(command), commands: [] };
		const traversalDeadline = performance.now() + MAX_PARSE_MS;
		const pending = [tree.rootNode];
		let visited = 0;
		while (pending.length > 0 && visited++ < MAX_NODES && performance.now() < traversalDeadline) {
			const node = pending.pop();
			if (!node) continue;
			// Recovery can mislabel heredoc/source text as commands. Keep only the valid prefix.
			if (node.type === "ERROR" || node.isMissing) break;
			if (node.type === "command" && !node.hasError) {
				const name = node.childForFieldName("name");
				if (name) {
					const arguments_ = node.childrenForFieldName("argument");
					// The grammar groups words after a redirect as additional destinations.
					if (node.parent?.type === "redirected_statement") {
						for (const redirect of node.parent.namedChildren) {
							if (redirect.type === "file_redirect") {
								for (const argument of redirect.childrenForFieldName("destination").slice(1)) arguments_.push(argument);
							} else if (redirect.type === "heredoc_redirect") {
								for (const argument of redirect.childrenForFieldName("argument")) arguments_.push(argument);
							}
						}
					}
					arguments_.sort((a, b) => a.startIndex - b.startIndex);
					inspectInvocation([literal(name), ...arguments_.map(literal)], result);
				}
			}
			const children = node.namedChildren;
			for (let i = children.length - 1; i >= 0; i--) pending.push(children[i]);
		}
		if (pending.length > 0 && (visited >= MAX_NODES || performance.now() >= traversalDeadline)) result.dangerous ||= hasWarningText(command);
		return result;
	} finally {
		tree?.delete();
		parser.reset();
	}
}
