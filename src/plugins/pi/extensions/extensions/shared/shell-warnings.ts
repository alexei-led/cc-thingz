import { basename } from "node:path";

const recursiveRm = /\brm\s+(?:(?:-[a-zA-Z]+|--[a-z]+(?:-[a-z]+)*)\s+)*(?:-[a-zA-Z]*[rR][a-zA-Z]*|--recursive)(?=\s|$)/;
const rawPatterns = [recursiveRm, /\bsudo\b/i, /\b(chmod|chown)\b.*777/i];
const runnerValueFlags: Record<string, readonly string[]> = {
	time: [],
	nohup: [],
	timeout: ["-s", "--signal", "-k", "--kill-after"],
	nice: ["-n", "--adjustment"],
	stdbuf: ["-i", "-o", "-e", "--input", "--output", "--error"],
	ionice: ["-c", "-n", "-p", "-P", "-u", "--class", "--classdata", "--pid", "--pgid", "--uid"],
	xargs: ["-n", "-P", "-L", "-s", "-E", "-I", "--max-args", "--max-procs", "--max-lines", "--max-chars", "--eof", "--replace"],
};

export function hasWarningText(command: string): boolean {
	return rawPatterns.some((pattern) => pattern.test(command));
}

// Warning classification only: never use this permissive scan to grant a rule.
// Interpreter source is opaque. Shell expansions retain the conservative raw check.
export function inspectShellWarnings(command: string): { dangerous: boolean; commands: string[][] } {
	let dangerous = false;
	const commands: string[][] = [];
	const words: string[] = [];
	let word = "";
	let active = false;
	let quote: "'" | '"' | undefined;
	const heredocs: Array<{ delimiter: string; quoted: boolean; stripTabs: boolean }> = [];
	const finishWord = () => {
		if (active) words.push(word);
		word = "";
		active = false;
	};
	const finishCommand = () => {
		finishWord();
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
				(name === "rm" && recursiveRm.test([name, ...args].join(" "))) ||
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
		if (quote === '"') {
			if (c === '"') quote = undefined;
			else word += c;
			if (c === "`" || (c === "$" && ["(", "{"].includes(command[i + 1]))) dangerous ||= hasWarningText(command.slice(i));
			continue;
		}
		if (c === "'" || c === '"') {
			quote = c;
			active = true;
			continue;
		}
		if (c === "`" || (c === "$" && ["(", "{"].includes(command[i + 1]))) dangerous ||= hasWarningText(command.slice(i));
		if (c === "#" && !active && (i === 0 || /[\s;|&()]/.test(command[i - 1]))) {
			const end = command.indexOf("\n", i);
			i = end === -1 ? command.length : end - 1;
			continue;
		}
		if (c === "<" && command[i + 1] === "<") {
			const match = /^<<(-?)[ \t]*(?:'([^'\n]+)'|"([^"\n]+)"|([a-zA-Z_][a-zA-Z0-9_]*))/.exec(command.slice(i));
			if (match) {
				finishWord();
				heredocs.push({ delimiter: match[2] ?? match[3] ?? match[4], quoted: !!(match[2] || match[3]), stripTabs: match[1] === "-" });
				i += match[0].length - 1;
				continue;
			}
		}
		if (c === "<" || c === ">") {
			if (active && !/^\d+$/.test(word)) finishWord();
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
							if (!doc.quoted && /\$\(|`/.test(body)) dangerous ||= hasWarningText(body);
							i = lineEnd;
							found = true;
							break;
						}
						if (end === -1) break;
						cursor = end + 1;
					}
					if (!found) {
						dangerous ||= hasWarningText(command.slice(bodyStart));
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
	if (quote) dangerous ||= hasWarningText(command);
	return { dangerous, commands };
}
