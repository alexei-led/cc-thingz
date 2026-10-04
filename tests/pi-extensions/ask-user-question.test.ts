import { describe, expect, it, mock } from "bun:test";

// typebox is a Pi peer dep, not installed in the project — mock before importing
mock.module("typebox", () => ({
	Type: {
		Object: (s: unknown) => s,
		String: () => ({}),
		Optional: (s: unknown) => s,
		Array: (s: unknown) => ({ items: s }),
		Boolean: () => ({}),
	},
}));
mock.module("@earendil-works/pi-coding-agent", () => ({}));

const { default: askUserQuestion, parseMultiSelect, wrapQuestionText } = await import("../../src/plugins/pi/extensions/extensions/ask-user-question.ts");

const OPTIONS = [
	{ label: "Alpha", value: "alpha" },
	{ label: "Beta", value: "beta" },
	{ label: "Gamma" }, // value defaults to label
];

describe("wrapQuestionText", () => {
	it("wraps long text to the requested width", () => {
		const lines = wrapQuestionText("alpha beta gamma delta", 20);
		expect(lines).toEqual(["alpha beta gamma", "delta"]);
	});

	it("caps long questions so options stay visible", () => {
		const lines = wrapQuestionText("word ".repeat(100), 20, 3);
		expect(lines).toHaveLength(3);
		expect(lines[2].endsWith("…")).toBe(true);
	});
});

describe("selection UI", () => {
	it("keeps single-select options visible after capping a long question", async () => {
		let registeredTool: any;
		askUserQuestion({
			registerTool(tool: any) {
				registeredTool = tool;
			},
		} as any);

		const select = mock(async () => "1. Yes");
		const result = await registeredTool.execute(
			"tool-call-id",
			{
				questions: [
					{
						header: "Decision",
						question: "word ".repeat(100),
						options: [
							{ label: "Yes", value: "yes" },
							{ label: "No", value: "no" },
						],
						allowOther: false,
					},
				],
			},
			undefined,
			undefined,
			{
				hasUI: true,
				mode: "rpc",
				ui: { select },
			},
		);

		expect(select).toHaveBeenCalledWith(expect.stringContaining("Decision"), ["1. Yes", "2. No"], expect.anything());
		expect(registeredTool.exposure).toBe("model-only");
		expect(result.content[0].text).toContain('"value":"yes"');
		expect(result.details.answers[0].answers).toEqual([{ label: "Yes", value: "yes", source: "option" }]);
	});

	it("keeps multi-select options visible after capping a long question", async () => {
		let registeredTool: any;
		askUserQuestion({
			registerTool(tool: any) {
				registeredTool = tool;
			},
		} as any);

		let prompt = "";
		const result = await registeredTool.execute(
			"tool-call-id",
			{
				questions: [
					{
						header: "Decision",
						question: "word ".repeat(200),
						options: [
							{ label: "Yes", value: "yes" },
							{ label: "No", value: "no" },
						],
						multiSelect: true,
						allowOther: false,
					},
				],
			},
			undefined,
			undefined,
			{
				hasUI: true,
				ui: {
					input: async (title: string) => {
						prompt = title;
						return "1,2";
					},
				},
			},
		);

		expect(prompt).toContain("1. Yes");
		expect(prompt).toContain("2. No");
		expect(prompt.split("\n").filter((line) => line.includes("word"))).toHaveLength(8);
		expect(result.details.answers[0].answers).toEqual([
			{ label: "Yes", value: "yes", source: "option" },
			{ label: "No", value: "no", source: "option" },
		]);
	});
});

describe("native question flow", () => {
	function tool() {
		let registered: any;
		askUserQuestion({
			registerTool: (value: any) => {
				registered = value;
			},
		} as any);
		return registered;
	}

	it("keeps duplicate labels and the Other label distinct", async () => {
		const registered = tool();
		const select = mock(async () => "2. Same — second");
		const result = await registered.execute(
			"id",
			{
				questions: [
					{
						question: "Pick",
						options: [
							{ label: "Same", description: "first", value: "a" },
							{ label: "Same", description: "second", value: "b" },
						],
					},
				],
			},
			undefined,
			undefined,
			{ hasUI: true, mode: "rpc", ui: { select } },
		);
		expect(result.details.answers[0].answers).toEqual([{ label: "Same", value: "b", source: "option" }]);
	});

	it.each([undefined, "unexpected"])("stops sequential questions on a cancelled or invalid selection: %s", async (selection) => {
		const registered = tool();
		const select = mock(async () => selection);
		const result = await registered.execute(
			"id",
			{
				questions: [
					{ question: "First", options: OPTIONS },
					{ question: "Second", options: OPTIONS },
				],
			},
			undefined,
			undefined,
			{ hasUI: true, ui: { select } },
		);
		expect(result.details.cancelled).toBe(true);
		expect(select).toHaveBeenCalledTimes(1);
	});

	it.each(["  custom value  ", "", undefined])("uses native input for Other and preserves cancellation: %s", async (inputValue) => {
		const registered = tool();
		const signal = new AbortController().signal;
		const input = mock(async () => inputValue);
		const result = await registered.execute("id", { questions: [{ question: "Pick", options: [{ label: "Only" }] }] }, signal, undefined, {
			hasUI: true,
			mode: "rpc",
			ui: { select: async () => "2. Other / type something", input },
		});
		expect(input).toHaveBeenCalledWith(expect.stringContaining("Pick"), undefined, { signal });
		expect(result.details.cancelled).toBe(inputValue === undefined);
		expect(result.details.answers[0].answers).toEqual(inputValue?.trim() ? [{ label: "custom value", value: "custom value", source: "custom" }] : []);
	});

	it("keeps the question visible when free text has a placeholder", async () => {
		const registered = tool();
		const input = mock(async () => " answer ");
		const result = await registered.execute(
			"id",
			{ questions: [{ header: "Decision", question: "Which path?", placeholder: "/path" }] },
			undefined,
			undefined,
			{ hasUI: true, mode: "rpc", ui: { input } },
		);
		expect(input).toHaveBeenCalledWith("Decision\nWhich path?", "/path", expect.anything());
		expect(result.details.answers[0].answers).toEqual([{ label: "answer", value: "answer", source: "custom" }]);
	});

	it.each([true, false])("uses blank native input for multi-select (allowOther=%s)", async (allowOther) => {
		const registered = tool();
		const input = mock(async () => "1, BETA, 1, custom");
		const result = await registered.execute(
			"id",
			{ questions: [{ question: "Pick several", options: OPTIONS, multiSelect: true, allowOther }] },
			undefined,
			undefined,
			{ hasUI: true, mode: "rpc", ui: { input } },
		);
		expect(result.details.answers[0].answers).toEqual([
			{ label: "Alpha", value: "alpha", source: "option" },
			{ label: "Beta", value: "beta", source: "option" },
			...(allowOther ? [{ label: "custom", value: "custom", source: "custom" }] : []),
		]);
	});

	it("does not open UI without a client", async () => {
		const result = await tool().execute("id", { questions: [{ question: "Pick" }] }, undefined, undefined, { hasUI: false });
		expect(result.isError).toBe(true);
	});
});

describe("parseMultiSelect", () => {
	it("parses single numeric index", () => {
		expect(parseMultiSelect("1", OPTIONS)).toEqual([{ label: "Alpha", value: "alpha", source: "option" }]);
	});

	it("parses multiple numeric indices", () => {
		const result = parseMultiSelect("1,3", OPTIONS);
		expect(result).toEqual([
			{ label: "Alpha", value: "alpha", source: "option" },
			{ label: "Gamma", value: "Gamma", source: "option" },
		]);
	});

	it("parses option labels case-insensitively", () => {
		const result = parseMultiSelect("BETA,alpha", OPTIONS);
		expect(result).toHaveLength(2);
		expect(result[0]).toMatchObject({ label: "Beta", source: "option" });
		expect(result[1]).toMatchObject({ label: "Alpha", source: "option" });
	});

	it("treats unrecognized input as custom value", () => {
		expect(parseMultiSelect("something custom", OPTIONS)).toEqual([
			{
				label: "something custom",
				value: "something custom",
				source: "custom",
			},
		]);
	});

	it("mixes numeric index, label, and custom", () => {
		const result = parseMultiSelect("1, beta, custom thing", OPTIONS);
		expect(result).toHaveLength(3);
		expect(result[0]).toMatchObject({ source: "option", label: "Alpha" });
		expect(result[1]).toMatchObject({ source: "option", label: "Beta" });
		expect(result[2]).toMatchObject({
			source: "custom",
			label: "custom thing",
		});
	});

	it("deduplicates repeated selections (numeric)", () => {
		expect(parseMultiSelect("1,1", OPTIONS)).toHaveLength(1);
	});

	it("deduplicates repeated selections (label after index)", () => {
		expect(parseMultiSelect("1,alpha", OPTIONS)).toHaveLength(1);
	});

	it("defaults value to label when option has no value field", () => {
		const [item] = parseMultiSelect("3", OPTIONS);
		expect(item.value).toBe("Gamma");
		expect(item.label).toBe("Gamma");
	});

	it("returns empty array for empty input", () => {
		expect(parseMultiSelect("", OPTIONS)).toEqual([]);
	});

	it("returns empty array for whitespace-only input", () => {
		expect(parseMultiSelect("   ", OPTIONS)).toEqual([]);
	});

	it("ignores out-of-range numeric index — treats as custom", () => {
		const result = parseMultiSelect("99", OPTIONS);
		expect(result[0]).toMatchObject({ source: "custom", label: "99" });
	});

	it("handles options array with single entry", () => {
		const result = parseMultiSelect("1", [{ label: "Only" }]);
		expect(result[0]).toMatchObject({
			label: "Only",
			value: "Only",
			source: "option",
		});
	});
});
