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
