/**
 * Pure utility functions for plan mode.
 * Extracted for testability.
 */

// This intentionally accepts a small shell subset, not arbitrary shell syntax.
// It is a workflow guard; executable resolution and repository config remain trusted.
interface InspectionOptions {
	flags: RegExp;
	values?: readonly string[];
}

const INSPECTION_COMMANDS: Record<string, InspectionOptions> = {
	cat: { flags: /^-[benstuvAET]+$/ },
	ls: { flags: /^-[laAdFhRrSt1]+$/ },
	pwd: { flags: /^-[LP]$/ },
	head: { flags: /^-(?:[qv]+|\d+)$/, values: ["-n", "-c"] },
	tail: { flags: /^-(?:[qv]+|\d+)$/, values: ["-n", "-c"] },
	wc: { flags: /^-[clmwL]+$/ },
	grep: { flags: /^(?:-[rinvElwFcsho]+|--(?:line-number|ignore-case|files-with-matches|fixed-strings))$/, values: ["-e", "-f", "-A", "-B", "-C", "-m", "--include", "--exclude"] },
	rg: { flags: /^(?:-[nvilwFcsoSU]+|--(?:files|hidden|no-ignore|line-number|ignore-case|fixed-strings|files-with-matches|count|json|no-heading))$/, values: ["-e", "-f", "-g", "-t", "-T", "-A", "-B", "-C", "-m", "--glob", "--type", "--max-count", "--max-depth"] },
	find: { flags: /^-(?:print|print0|empty|a|o|not)$/, values: ["-name", "-iname", "-path", "-ipath", "-type", "-maxdepth", "-mindepth", "-size", "-mtime"] },
	jq: { flags: /^-[rcesM]+$/ },
	sort: { flags: /^-[nrfbu]+$/ },
	diff: { flags: /^-[uqrwB]+$/ },
};

const GIT_INSPECTION: Record<string, InspectionOptions> = {
	status: { flags: /^(?:-[sb]+|--(?:short|branch|porcelain(?:=v[12])?|untracked-files(?:=(?:no|normal|all))?))$/ },
	log: { flags: /^(?:-\d+|--(?:oneline|stat|name-only|name-status|all|graph|decorate|no-decorate|reverse|no-merges|no-ext-diff|no-textconv))$/, values: ["-n", "--max-count", "--since", "--until", "--author", "--grep"] },
	diff: { flags: /^(?:--(?:stat|numstat|shortstat|name-only|name-status|cached|staged|check|no-ext-diff|no-textconv)|-[Uw]\d*)$/ },
	show: { flags: /^(?:--(?:stat|name-only|name-status|oneline|no-patch|no-ext-diff|no-textconv))$/ },
	"ls-files": { flags: /^(?:-[zcmots]+|--(?:cached|modified|others|exclude-standard|stage))$/ },
};

function inspectionArgs(args: string[], options: InspectionOptions): boolean {
	for (let i = 0; i < args.length; i++) {
		const arg = args[i];
		if (arg === "--") return true;
		if (!arg.startsWith("-")) continue;
		const equals = arg.indexOf("=");
		const name = equals < 0 ? arg : arg.slice(0, equals);
		if (options.values?.includes(name)) {
			if (equals >= 0) {
				if (equals === arg.length - 1) return false;
			} else if (++i >= args.length) return false;
			continue;
		}
		if (!options.flags.test(arg)) return false;
	}
	return true;
}

export function isSafeCommand(command: string): boolean {
	// No expansion, escaping, operators, redirection, comments or multiline input.
	// Quotes may group literal words, but do not expand the supported syntax.
	if (/[\x00-\x1f\x7f$`\\;<>|&(){}#!]/.test(command)) return false;
	const tokens = command.match(/'[^']*'|"[^"]*"|[^\s'"]+/g);
	if (!tokens || tokens.join(" ") !== command.trim().replace(/ +/g, " ")) return false;
	if (tokens.some((token) => !/^["']/.test(token) && /[*?\[\]]/.test(token))) return false;
	const args = tokens.map((token) => /^["']/.test(token) ? token.slice(1, -1) : token);
	const name = args.shift();
	if (name === "git") {
		while (args[0] === "-C" || args[0] === "--no-pager" || args[0] === "--no-optional-locks") {
			if (args.shift() === "-C" && !args.shift()) return false;
		}
		const subcommand = args.shift();
		const options = subcommand && Object.hasOwn(GIT_INSPECTION, subcommand) && GIT_INSPECTION[subcommand];
		return !!options && inspectionArgs(args, options);
	}
	if (name === "find" && args.includes("--")) return false;
	const options = name && Object.hasOwn(INSPECTION_COMMANDS, name) && INSPECTION_COMMANDS[name];
	return !!options && inspectionArgs(args, options);
}

export interface TodoItem {
	step: number;
	text: string;
	completed: boolean;
}

export function cleanStepText(text: string): string {
	let cleaned = text
		.replace(/\*{1,2}([^*]+)\*{1,2}/g, "$1") // Remove bold/italic
		.replace(/`([^`]+)`/g, "$1") // Remove code
		.replace(/^(Use|Run|Execute|Create|Write|Read|Check|Verify|Update|Modify|Add|Remove|Delete|Install)\s+(the\s+)?/i, "")
		.replace(/\s+/g, " ")
		.trim();

	if (cleaned.length > 0) {
		cleaned = cleaned.charAt(0).toUpperCase() + cleaned.slice(1);
	}
	if (cleaned.length > 50) {
		cleaned = `${cleaned.slice(0, 47)}...`;
	}
	return cleaned;
}

export function extractTodoItems(message: string): TodoItem[] {
	const items: TodoItem[] = [];
	const headerMatch = message.match(/\*{0,2}Plan:\*{0,2}\s*\n/i);
	if (!headerMatch) return items;

	const planSection = message.slice(message.indexOf(headerMatch[0]) + headerMatch[0].length);
	const numberedPattern = /^\s*(\d+)[.)]\s+\*{0,2}([^*\n]+)/gm;

	for (const match of planSection.matchAll(numberedPattern)) {
		const text = match[2]
			.trim()
			.replace(/\*{1,2}$/, "")
			.trim();
		if (text.length > 5 && !text.startsWith("`") && !text.startsWith("/") && !text.startsWith("-")) {
			const cleaned = cleanStepText(text);
			if (cleaned.length > 3) {
				items.push({ step: items.length + 1, text: cleaned, completed: false });
			}
		}
	}
	return items;
}

export function extractDoneSteps(message: string): number[] {
	const steps: number[] = [];
	for (const match of message.matchAll(/\[DONE:(\d+)\]/gi)) {
		const step = Number(match[1]);
		if (Number.isFinite(step)) steps.push(step);
	}
	return steps;
}

export function markCompletedSteps(text: string, items: TodoItem[]): number {
	const doneSteps = extractDoneSteps(text);
	for (const step of doneSteps) {
		const item = items.find((t) => t.step === step);
		if (item) item.completed = true;
	}
	return doneSteps.length;
}
