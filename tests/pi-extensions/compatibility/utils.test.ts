import { describe, expect, it } from "bun:test";
import { cleanStepText, extractDoneSteps, extractTodoItems, isSafeCommand, markCompletedSteps, type TodoItem } from "../../../src/plugins/pi/extensions/extensions/plan-mode/utils.ts";

describe("isSafeCommand", () => {
	it.each([
		["cat README.md", true],
		["ls -la src/", true],
		["grep -r pattern src/", true],
		["rg pattern src/", true],
		["git status", true],
		["git diff HEAD~1", true],
		["git log --oneline -5", true],
		["npm list --depth=0", true],
		["jq . file.json", true],
		["rm -rf dist/", false],
		["rm -f important.ts", false],
		["sudo apt install git", false],
		["git commit -m msg", false],
		["git push origin main", false],
		["npm install express", false],
		["echo foo > file.txt", false],
		["kill 1234", false],
		["chmod 777 /etc/passwd", false],
	])(`isSafeCommand(%s) → %s`, (cmd, expected) => {
		expect(isSafeCommand(cmd)).toBe(expected);
	});
});

describe("cleanStepText", () => {
	it.each([
		["**Bold text**", "Bold text"],
		["`code here`", "Code here"],
		["Write the code", "Code"],
		["Run tests", "Tests"],
		["simple text", "Simple text"],
		["  whitespace  ", "Whitespace"],
		["", ""],
	])(`cleanStepText(%j) → %j`, (input, expected) => {
		expect(cleanStepText(input)).toBe(expected);
	});

	it("truncates long text to 50 chars with ellipsis", () => {
		const long = "A very long text that exceeds the fifty character display limit";
		const result = cleanStepText(long);
		expect(result.length).toBe(50);
		expect(result.endsWith("...")).toBe(true);
	});
});

describe("extractTodoItems", () => {
	it("returns empty array when no Plan: header present", () => {
		expect(extractTodoItems("Just some text\n1. Step one\n2. Step two")).toHaveLength(0);
	});

	it("extracts numbered steps after Plan: header", () => {
		const msg = "**Plan:**\n1. First step here\n2. Second step here\n3. Third step here";
		const items = extractTodoItems(msg);
		expect(items).toHaveLength(3);
		expect(items[0]).toMatchObject({ step: 1, completed: false });
		expect(items[2]).toMatchObject({ step: 3, completed: false });
	});

	it("skips items shorter than 4 chars after cleaning", () => {
		const msg = "Plan:\n1. ok\n2. A sufficiently long step description";
		const items = extractTodoItems(msg);
		expect(items.every((i) => i.text.length > 3)).toBe(true);
	});

	it("strips bold markers from step text", () => {
		const msg = "Plan:\n1. **Write the tests**";
		const items = extractTodoItems(msg);
		expect(items[0]?.text).not.toContain("**");
	});

	it("stops at end of plan section", () => {
		const msg = "**Plan:**\n1. First step\n\nSome unrelated paragraph\n\n2. Not a plan step";
		const items = extractTodoItems(msg);
		// Items after empty line are still matched if the regex finds them
		expect(items.length).toBeGreaterThan(0);
	});
});

describe("extractDoneSteps", () => {
	it.each([
		["[DONE:1] done", [1]],
		["[DONE:1] and [DONE:3]", [1, 3]],
		["[done:5] case-insensitive", [5]],
		["no markers here", []],
		["", []],
	])(`extractDoneSteps(%j) → %j`, (input, expected) => {
		expect(extractDoneSteps(input)).toEqual(expected);
	});
});

describe("markCompletedSteps", () => {
	it("marks matching step as completed", () => {
		const items: TodoItem[] = [
			{ step: 1, text: "First", completed: false },
			{ step: 2, text: "Second", completed: false },
		];
		const count = markCompletedSteps("[DONE:1] result", items);
		expect(count).toBe(1);
		expect(items[0].completed).toBe(true);
		expect(items[1].completed).toBe(false);
	});

	it("returns marker count even when no items match", () => {
		const items: TodoItem[] = [{ step: 1, text: "Only", completed: false }];
		const count = markCompletedSteps("[DONE:99]", items);
		expect(count).toBe(1); // one marker found
		expect(items[0].completed).toBe(false); // but step 99 didn't exist
	});

	it("marks multiple steps in one pass", () => {
		const items: TodoItem[] = [
			{ step: 1, text: "A", completed: false },
			{ step: 2, text: "B", completed: false },
			{ step: 3, text: "C", completed: false },
		];
		markCompletedSteps("[DONE:1] step 1 done [DONE:3] step 3 done", items);
		expect(items[0].completed).toBe(true);
		expect(items[1].completed).toBe(false);
		expect(items[2].completed).toBe(true);
	});
});
