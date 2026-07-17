import type { ExtensionAPI, ExtensionContext } from "@earendil-works/pi-coding-agent";
import { Key, matchesKey, truncateToWidth } from "@earendil-works/pi-tui";
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

type DisplayOption = (AskOption & { isOther: false }) | { label: string; description?: string; isOther: true };

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
const MULTI_SELECT_PROMPT_WIDTH = 80;

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

export function parseMultiSelect(input: string, options: AskOption[]): Array<{ label: string; value: string; source: "option" | "custom" }> {
	const rawParts = input
		.split(",")
		.map((part) => part.trim())
		.filter(Boolean);

	const answers: Array<{ label: string; value: string; source: "option" | "custom" }> = [];
	const seen = new Set<string>();

	for (const part of rawParts) {
		const asNumber = Number(part);
		if (Number.isInteger(asNumber) && asNumber >= 1 && asNumber <= options.length) {
			const option = options[asNumber - 1];
			const key = `option:${normalizeValue(option)}`;
			if (!seen.has(key)) {
				answers.push({ label: option.label, value: normalizeValue(option), source: "option" });
				seen.add(key);
			}
			continue;
		}

		const match = options.find((option) => option.label.toLowerCase() === part.toLowerCase());
		if (match) {
			const key = `option:${normalizeValue(match)}`;
			if (!seen.has(key)) {
				answers.push({ label: match.label, value: normalizeValue(match), source: "option" });
				seen.add(key);
			}
			continue;
		}

		const key = `custom:${part}`;
		if (!seen.has(key)) {
			answers.push({ label: part, value: part, source: "custom" });
			seen.add(key);
		}
	}

	return answers;
}

async function askOne(question: AskQuestion, ctx: ExtensionContext): Promise<Answer> {
	const header = question.header ?? "Question";
	const options = question.options ?? [];
	const multiSelect = question.multiSelect === true;
	const allowOther = question.allowOther ?? options.length > 0;

	if (options.length === 0) {
		const input = await ctx.ui.input(header, question.placeholder ?? question.question);
		if (input === undefined) {
			return { question: question.question, header: question.header, multiSelect: false, cancelled: true, answers: [] };
		}

		const value = input.trim();
		if (!value) {
			return { question: question.question, header: question.header, multiSelect: false, cancelled: false, answers: [] };
		}

		return {
			question: question.question,
			header: question.header,
			multiSelect: false,
			cancelled: false,
			answers: [{ label: value, value, source: "custom" }],
		};
	}

	if (!multiSelect) {
		const displayOptions: DisplayOption[] = options.map((option) => ({ ...option, isOther: false }));
		if (allowOther) displayOptions.push({ label: "Other / type something", isOther: true });

		const selectedIndex = await ctx.ui.custom<number | undefined>((tui, theme, _keybindings, done) => {
			let optionIndex = 0;

			function refresh() {
				tui.requestRender();
			}

			function selectCurrent() {
				done(optionIndex);
			}

			function handleInput(data: string) {
				if (matchesKey(data, Key.up)) {
					optionIndex = Math.max(0, optionIndex - 1);
					refresh();
					return;
				}
				if (matchesKey(data, Key.down)) {
					optionIndex = Math.min(displayOptions.length - 1, optionIndex + 1);
					refresh();
					return;
				}
				if (matchesKey(data, Key.enter)) {
					selectCurrent();
					return;
				}
				if (matchesKey(data, Key.escape)) {
					done(undefined);
					return;
				}

				const numeric = Number(data);
				if (Number.isInteger(numeric) && numeric >= 1 && numeric <= displayOptions.length) {
					optionIndex = numeric - 1;
					selectCurrent();
				}
			}

			function render(width: number): string[] {
				const safeWidth = Math.max(20, width);
				const lines: string[] = [];
				const add = (value: string) => lines.push(truncateToWidth(value, safeWidth));

				add(theme.fg("accent", "─".repeat(safeWidth)));
				add(theme.fg("accent", theme.bold(` ${header}`)));
				lines.push("");
				for (const line of wrapQuestionText(question.question, safeWidth - 2)) {
					add(` ${theme.fg("text", line)}`);
				}
				lines.push("");

				for (let i = 0; i < displayOptions.length; i++) {
					const option = displayOptions[i];
					const selected = i === optionIndex;
					const prefix = selected ? theme.fg("accent", "→ ") : "  ";
					const label = `${i + 1}. ${option.label}`;
					add(prefix + theme.fg(selected ? "accent" : "text", label));
					if (option.description) add(`    ${theme.fg("muted", option.description)}`);
				}

				lines.push("");
				add(theme.fg("dim", " ↑↓ navigate • Enter select • Esc cancel • number quick-select"));
				add(theme.fg("accent", "─".repeat(safeWidth)));
				return lines;
			}

			return { render, invalidate: () => {}, handleInput };
		});

		if (selectedIndex === undefined) {
			return { question: question.question, header: question.header, multiSelect: false, cancelled: true, answers: [] };
		}

		const selected = displayOptions[selectedIndex];
		if (!selected) {
			return { question: question.question, header: question.header, multiSelect: false, cancelled: true, answers: [] };
		}
		if (selected.isOther) {
			const custom = await ctx.ui.input(header, question.placeholder ?? question.question);
			if (custom === undefined) {
				return { question: question.question, header: question.header, multiSelect: false, cancelled: true, answers: [] };
			}
			const value = custom.trim();
			return {
				question: question.question,
				header: question.header,
				multiSelect: false,
				cancelled: false,
				answers: value ? [{ label: value, value, source: "custom" }] : [],
			};
		}

		return {
			question: question.question,
			header: question.header,
			multiSelect: false,
			cancelled: false,
			answers: [{ label: selected.label, value: normalizeValue(selected), source: "option" }],
		};
	}

	const numberedOptions = options.map(formatOption).join("\n");
	const promptLines = [
		...wrapQuestionText(question.question, MULTI_SELECT_PROMPT_WIDTH),
		"",
		numberedOptions,
		"",
		"Enter comma-separated option numbers or labels.",
	];

	if (allowOther) {
		promptLines.push("Custom values are allowed too.");
	} else {
		promptLines.push("Use only the listed options.");
	}

	const input = await ctx.ui.editor(header, promptLines.join("\n"));
	if (input === undefined) {
		return { question: question.question, header: question.header, multiSelect: true, cancelled: true, answers: [] };
	}

	let answers = parseMultiSelect(input, options);
	if (!allowOther) {
		answers = answers.filter((answer) => answer.source === "option");
	}

	return {
		question: question.question,
		header: question.header,
		multiSelect: true,
		cancelled: false,
		answers,
	};
}

export default function askUserQuestion(pi: ExtensionAPI) {
	pi.registerTool({
		name: "ask_user_question",
		label: "Ask User Question",
		description: "Ask the user structured questions. Use for one-question-at-a-time clarification, scoped choices, or short free-text answers.",
		promptSnippet: "Ask the user a structured question and get a machine-readable answer.",
		promptGuidelines: [
			"Use ask_user_question when you need the user's choice before proceeding.",
			"Use ask_user_question for one question at a time. Prefer single-select options over open-ended text when possible.",
		],
		parameters: AskUserQuestionParams,
		async execute(_toolCallId, params, _signal, _onUpdate, ctx) {
			if (!ctx.hasUI) {
				return {
					content: [{ type: "text", text: "Error: ask_user_question requires interactive UI" }],
					details: { questions: params.questions, answers: [], cancelled: true },
					isError: true,
				};
			}

			if (params.questions.length === 0) {
				return {
					content: [{ type: "text", text: "Error: no questions provided" }],
					details: { questions: [], answers: [], cancelled: true },
					isError: true,
				};
			}

			const answers: Answer[] = [];
			for (const question of params.questions) {
				const answer = await askOne(question, ctx);
				answers.push(answer);
				if (answer.cancelled) {
					return {
						content: [{ type: "text", text: `User cancelled: ${question.question}` }],
						details: { questions: params.questions, answers, cancelled: true },
					};
				}
			}

			const summary = answers
				.map((answer) => {
					const rendered = answer.answers.map((item) => item.label).join(", ") || "(empty)";
					return `${answer.question}: ${rendered}`;
				})
				.join("\n");

			return {
				content: [{ type: "text", text: summary }],
				details: { questions: params.questions, answers, cancelled: false },
			};
		},
	});
}
