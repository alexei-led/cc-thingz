import { basename } from "node:path";

const recursiveRm = /\brm\s+(?:(?:-[a-zA-Z]+|--[a-z]+(?:-[a-z]+)*)\s+)*(?:-[a-zA-Z]*[rR][a-zA-Z]*|--recursive)(?=\s|$)/;
const rawPatterns = [recursiveRm, /\bsudo\b/i, /\b(chmod|chown)\b.*777/i];
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

export function hasWarningText(command: string): boolean {
	return rawPatterns.some((pattern) => pattern.test(command));
}

function readExpansion(source: string, start: number): { body: string; end: number } | undefined {
	const backtick = source[start] === "`";
	const open = backtick ? "`" : source[start + 1];
	const close = backtick ? "`" : open === "(" ? ")" : "}";
	const bodyStart = start + (backtick ? 1 : 2);
	let depth = 1;
	let quote: "'" | '"' | undefined;
	for (let i = bodyStart; i < source.length; i++) {
		const c = source[i];
		if (c === "\\") {
			i++;
			continue;
		}
		if (backtick && c === "`") return { body: source.slice(bodyStart, i), end: i };
		if (quote === "'") {
			if (c === "'") quote = undefined;
			continue;
		}
		if (c === "`" || (c === "$" && ["(", "{"].includes(source[i + 1]))) {
			const nested = readExpansion(source, i);
			if (nested) {
				i = nested.end;
				continue;
			}
		}
		if (c === "'" || c === '"') {
			if (!quote) quote = c;
			else if (quote === c) quote = undefined;
			continue;
		}
		if (!quote) {
			if (c === open) depth++;
			if (c === close && --depth === 0) return { body: source.slice(bodyStart, i), end: i };
		}
	}
	return undefined;
}

function readHeredoc(source: string, start: number): { delimiter: string; quoted: boolean; stripTabs: boolean; end: number } | undefined {
	const operator = /^<<(-?)[ \t]*/.exec(source.slice(start));
	if (!operator || source[start + 2] === "<") return undefined;
	let delimiter = "";
	let quoted = false;
	let quote: "'" | '"' | undefined;
	let i = start + operator[0].length;
	for (; i < source.length; i++) {
		const c = source[i];
		if (quote) {
			if (c === quote) quote = undefined;
			else if (quote === '"' && c === "\\" && ["$", "`", '"', "\\", "\n"].includes(source[i + 1])) {
				if (source[++i] !== "\n") delimiter += source[i];
			} else delimiter += c;
		} else if (c === "'" || c === '"') {
			quoted = true;
			quote = c;
		} else if (c === "\\") {
			quoted = true;
			if (source[++i] !== "\n") delimiter += source[i] ?? "";
		} else if (/[\s;|&()<>]/.test(c)) break;
		else delimiter += c;
	}
	return (delimiter || quoted) && !quote ? { delimiter, quoted, stripTabs: operator[1] === "-", end: i - 1 } : undefined;
}

// Warning/deny classification only. The stricter literal parser alone grants exceptions.
// Interpreter source is opaque; substitutions are inspected as local shell commands.
export function inspectShellWarnings(command: string, context: "shell" | "parameter" | "heredoc" = "shell"): { dangerous: boolean; commands: string[][] } {
	let dangerous = false;
	const commands: string[][] = [];
	const words: string[] = [];
	const redirects: boolean[] = [];
	let redirect = false;
	let word = "";
	let active = false;
	let quote: "'" | '"' | undefined;
	const heredocs: Array<{ delimiter: string; quoted: boolean; stripTabs: boolean }> = [];
	const finishWord = () => {
		if (active) {
			words.push(word);
			redirects.push(redirect);
		}
		word = "";
		redirect = false;
		active = false;
	};
	const finishCommand = () => {
		finishWord();
		const argv: string[] = [];
		for (let j = 0; context === "shell" && j < words.length; j++) {
			if (redirects[j]) {
				const operator = /^\d*(?:[<>]&|[<>]{1,2})(.*)$/.exec(words[j]);
				if (operator && !operator[1]) j++;
			} else argv.push(words[j]);
		}
		words.splice(0, words.length, ...argv);
		redirects.length = 0;
		if (words.length > 0) commands.push([...words]);
		let i = 0;
		while (i < words.length) {
			const redirect = /^\d*(?:[<>]{1,2}|[<>]&)(.*)$/.exec(words[i]);
			if (redirect) {
				i += redirect[1] ? 1 : 2;
				continue;
			}
			if (/^[a-zA-Z_][a-zA-Z0-9_]*=/.test(words[i]) || ["if", "then", "elif", "else", "do", "while", "until", "!"].includes(words[i])) {
				i++;
				continue;
			}
			const wrapper = basename(words[i]);
			if (wrapper === "env") {
				i++;
				while (i < words.length && words[i].startsWith("-")) {
					if (words[i] === "-S" || words[i] === "--split-string") {
						const nested = inspectShellWarnings(words.slice(i + 1).join(" "));
						dangerous ||= nested.dangerous;
						commands.push(...nested.commands);
						i = words.length;
						break;
					}
					i += words[i] === "-u" || words[i] === "--unset" ? 2 : 1;
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
					if (words[i] === "--" || (wrapper === "command" ? words[i] === "-p" : ["-c", "-l"].includes(words[i]))) {
						i++;
						continue;
					}
					break;
				}
				continue;
			}
			if (Object.hasOwn(runnerValueFlags, wrapper)) {
				i++;
				while (i < words.length && words[i].startsWith("-")) {
					if (words[i] === "--") {
						i++;
						break;
					}
					i += runnerValueFlags[wrapper].includes(words[i]) ? 2 : 1;
				}
				if (wrapper === "timeout") i++;
				continue;
			}
			break;
		}
		const executable = words[i];
		if (executable) {
			if (i > 0) commands.push(words.slice(i));
			const name = basename(executable);
			const args = words.slice(i + 1);
			if (name === "find") {
				for (let j = 0; j < args.length; j++) {
					if (!["-exec", "-execdir", "-ok", "-okdir"].includes(args[j])) continue;
					const end = args.findIndex((arg, index) => index > j && (arg === ";" || arg === "+"));
					const source = args
						.slice(j + 1, end < 0 ? undefined : end)
						.map((arg) => "'" + arg.replaceAll("'", "'\\''") + "'")
						.join(" ");
					const nested = inspectShellWarnings(source);
					dangerous ||= nested.dangerous;
					commands.push(...nested.commands);
					j = end < 0 ? args.length : end;
				}
			}
			if (
				name === "sudo" ||
				(name === "rm" &&
					args
						.slice(0, args.includes("--") ? args.indexOf("--") : undefined)
						.some((arg) => arg === "--recursive" || (/^-[a-zA-Z]+$/.test(arg) && /[rR]/.test(arg)))) ||
				((name === "chmod" || name === "chown") && args.some((arg) => /^[0-7]?777$/.test(arg)))
			)
				dangerous = true;
		}
		words.length = 0;
	};
	for (let i = 0; i < command.length; i++) {
		const c = command[i];
		if (quote === "'") {
			if (c === "'") quote = undefined;
			else word += c;
			continue;
		}
		if (c === "\\") {
			if (command[i + 1] !== "\n") {
				word += command[i + 1] ?? "";
				active = true;
			}
			i++;
			continue;
		}
		if (c === "`" || (c === "$" && ["(", "{"].includes(command[i + 1]))) {
			const expansion = readExpansion(command, i);
			if (expansion) {
				const nested = inspectShellWarnings(expansion.body, command[i + 1] === "{" ? "parameter" : "shell");
				dangerous ||= nested.dangerous;
				commands.push(...nested.commands);
				word += command.slice(i, expansion.end + 1);
				active = true;
				i = expansion.end;
				continue;
			}
		}
		if (quote === '"') {
			if (c === '"') quote = undefined;
			else word += c;
			continue;
		}
		if (context !== "heredoc" && (c === "'" || c === '"')) {
			quote = c;
			active = true;
			continue;
		}
		if (context !== "heredoc" && c === "#" && !active && (i === 0 || /[\s;|&()]/.test(command[i - 1]))) {
			const end = command.indexOf("\n", i);
			i = end === -1 ? command.length : end - 1;
			continue;
		}
		if (context !== "heredoc" && c === "<" && command[i + 1] === "<" && command[i - 1] !== "<") {
			const doc = readHeredoc(command, i);
			if (doc) {
				finishWord();
				heredocs.push(doc);
				i = doc.end;
				continue;
			}
		}
		if (c === "<" || c === ">") {
			if (active && !/^\d+$/.test(word)) finishWord();
			redirect = true;
			word += c;
			active = true;
			continue;
		}
		if (c === " " || c === "\t") finishWord();
		else if (";|&\n(){}".includes(c) && !(c === "&" && /[<>]/.test(command[i - 1] ?? ""))) {
			finishCommand();
			if (c === "\n") {
				for (const doc of heredocs.splice(0)) {
					const bodyStart = i + 1;
					let cursor = bodyStart;
					let found = false;
					while (cursor <= command.length) {
						const end = command.indexOf("\n", cursor);
						const lineEnd = end === -1 ? command.length : end;
						let line = command.slice(cursor, lineEnd);
						if (doc.stripTabs) line = line.replace(/^\t+/, "");
						if (line === doc.delimiter) {
							const body = command.slice(bodyStart, cursor);
							if (!doc.quoted) {
								const nested = inspectShellWarnings(body, "heredoc");
								dangerous ||= nested.dangerous;
								commands.push(...nested.commands);
							}
							i = lineEnd;
							found = true;
							break;
						}
						if (end === -1) break;
						cursor = end + 1;
					}
					if (!found) {
						if (!doc.quoted) {
							const nested = inspectShellWarnings(command.slice(bodyStart), "heredoc");
							dangerous ||= nested.dangerous;
							commands.push(...nested.commands);
						}
						i = command.length;
					}
				}
			}
		} else {
			word += c;
			active = true;
		}
	}
	finishCommand();
	return { dangerous, commands };
}
