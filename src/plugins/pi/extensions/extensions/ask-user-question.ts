import type { ExtensionAPI, ExtensionContext } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";

type AskOption = {
	label: string;
	description?: string;
	value?: string;
};

type AskQuestion = {
	question: string;
	header?: string;
	options?: AskOption[];
	multiSelect?: boolean;
	allowOther?: boolean;
	placeholder?: string;
};

type Answer = {
	question: string;
	header?: string;
	multiSelect: boolean;
	cancelled: boolean;
	answers: Array<{
		label: string;
		value: string;
		source: "option" | "custom";
	}>;
};

const AskOptionSchema = Type.Object({
	label: Type.String({ description: "Display label for the option" }),
	description: Type.Optional(Type.String({ description: "Optional extra context for the option" })),
	value: Type.Optional(Type.String({ description: "Optional machine-readable value; defaults to label" })),
});

const AskQuestionSchema = Type.Object({
	question: Type.String({ description: "Question text shown to the user" }),
	header: Type.Optional(Type.String({ description: "Short title shown above the question" })),
	options: Type.Optional(Type.Array(AskOptionSchema, { description: "Selectable options. Omit for free-text input." })),
	multiSelect: Type.Optional(Type.Boolean({ description: "Allow selecting multiple options. Defaults to false." })),
	allowOther: Type.Optional(Type.Boolean({ description: "Allow free-text answer in addition to listed options. Defaults to true when options exist." })),
	placeholder: Type.Optional(Type.String({ description: "Placeholder text for free-text input" })),
});

const AskUserQuestionParams = Type.Object({
	questions: Type.Array(AskQuestionSchema, {
		description: "Questions to ask. Ask them sequentially. Prefer one question per tool call.",
	}),
});

function formatOption(option: AskOption, index: number): string {
	return option.description ? `${index + 1}. ${option.label} — ${option.description}` : `${index + 1}. ${option.label}`;
}

function normalizeValue(option: AskOption): string {
	return option.value ?? option.label;
}

const MAX_QUESTION_LINES = 8;
const PROMPT_WIDTH = 80;

export function wrapQuestionText(text: string, width: number, maxLines = MAX_QUESTION_LINES): string[] {
	const usableWidth = Math.max(20, width);
	const wrapped: string[] = [];

	for (const rawLine of text.trim().split(/\r?\n/)) {
		const words = rawLine.trim().split(/\s+/).filter(Boolean);
		if (words.length === 0) {
			wrapped.push("");
			continue;
		}

		let line = "";
		for (const word of words) {
			const next = line ? `${line} ${word}` : word;
			if (next.length <= usableWidth) {
				line = next;
				continue;
			}
			if (line) wrapped.push(line);
			line = word;
		}
		if (line) wrapped.push(line);
	}

	if (wrapped.length <= maxLines) return wrapped;
	const visible = wrapped.slice(0, maxLines);
	visible[maxLines - 1] = `${visible[maxLines - 1].replace(/[.…\s]+$/, "")}…`;
	return visible;
}

export function parseMultiSelect(input: string, options: AskOption[]): Answer["answers"] {
	const rawParts = input
		.split(",")
		.map((part) => part.trim())
		.filter(Boolean);
	const answers: Answer["answers"] = [];
	const seen = new Set<string>();

	for (const part of rawParts) {
		const asNumber = Number(part);
		const option =
			Number.isInteger(asNumber) && asNumber >= 1 && asNumber <= options.length
				? options[asNumber - 1]
				: options.find((candidate) => candidate.label.toLowerCase() === part.toLowerCase());
		const value = option ? normalizeValue(option) : part;
		const source = option ? "option" : "custom";
		const key = `${source}:${value}`;
		if (!seen.has(key)) {
			answers.push({ label: option?.label ?? part, value, source });
			seen.add(key);
		}
	}

	return answers;
}

async function askOne(question: AskQuestion, ctx: ExtensionContext, signal?: AbortSignal): Promise<Answer> {
	const options = question.options ?? [];
	const multiSelect = options.length > 0 && question.multiSelect === true;
	const allowOther = question.allowOther ?? options.length > 0;
	const title = [question.header ?? "Question", ...wrapQuestionText(question.question, PROMPT_WIDTH)].join("\n");
	const answer: Answer = { question: question.question, header: question.header, multiSelect, cancelled: false, answers: [] };
	const dialogOptions = { signal };

	if (options.length === 0) {
		const input = await ctx.ui.input(title, question.placeholder, dialogOptions);
		answer.cancelled = input === undefined;
		const value = input?.trim();
		if (value) answer.answers.push({ label: value, value, source: "custom" });
		return answer;
	}

	if (!multiSelect) {
		const choices = options.map(formatOption);
		if (allowOther) choices.push(`${options.length + 1}. Other / type something`);
		const selected = await ctx.ui.select(title, choices, dialogOptions);
		const selectedIndex = selected === undefined ? -1 : choices.indexOf(selected);
		if (selectedIndex < 0) {
			answer.cancelled = true;
			return answer;
		}
		if (selectedIndex === options.length) {
			const input = await ctx.ui.input(title, question.placeholder, dialogOptions);
			answer.cancelled = input === undefined;
			const value = input?.trim();
			if (value) answer.answers.push({ label: value, value, source: "custom" });
		} else {
			const option = options[selectedIndex];
			answer.answers.push({ label: option.label, value: normalizeValue(option), source: "option" });
		}
		return answer;
	}

	// Pi has no native multi-select dialog. A blank input avoids treating editor
	// instructions as answers and works with both TUI and RPC clients.
	const prompt = [
		title,
		"",
		...options.map(formatOption),
		"",
		"Enter comma-separated option numbers or labels.",
		allowOther ? "Custom values are allowed too." : "Use only the listed options.",
	].join("\n");
	const input = await ctx.ui.input(prompt, question.placeholder ?? "1, 2", dialogOptions);
	answer.cancelled = input === undefined;
	answer.answers = parseMultiSelect(input ?? "", options).filter((item) => allowOther || item.source === "option");
	return answer;
}

export default function askUserQuestion(pi: ExtensionAPI) {
	pi.registerTool({
		name: "ask_user_question",
		label: "Ask User Question",
		exposure: "model-only",
		description: "Ask the user structured questions. Use for one-question-at-a-time clarification, scoped choices, or short free-text answers.",
		promptSnippet: "Ask the user a structured question and get a machine-readable answer.",
		promptGuidelines: [
			"Use ask_user_question when you need the user's choice before proceeding.",
			"Use ask_user_question for one question at a time. Prefer single-select options over open-ended text when possible.",
		],
		parameters: AskUserQuestionParams,
		async execute(_toolCallId, params, signal, _onUpdate, ctx) {
			if (!ctx.hasUI || params.questions.length === 0) {
				return {
					content: [{ type: "text", text: ctx.hasUI ? "Error: no questions provided" : "Error: ask_user_question requires interactive UI" }],
					details: { questions: params.questions, answers: [], cancelled: true },
					isError: true,
				};
			}

			const answers: Answer[] = [];
			for (const question of params.questions) {
				const answer = await askOne(question, ctx, signal);
				answers.push(answer);
				if (answer.cancelled) break;
			}
			const details = { questions: params.questions, answers, cancelled: answers.some((answer) => answer.cancelled) };
			return { content: [{ type: "text", text: JSON.stringify(details) }], details };
		},
	});
}
