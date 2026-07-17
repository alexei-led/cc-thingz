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
mock.module("@earendil-works/pi-tui", () => ({
  Key: { down: "down", enter: "enter", escape: "escape", up: "up" },
  matchesKey: (data: string, key: string) => data === key,
  truncateToWidth: (value: string, width: number) => value.slice(0, width),
}));

const {
  default: askUserQuestion,
  parseMultiSelect,
  wrapQuestionText,
} = await import("../../src/plugins/pi/extensions/extensions/ask-user-question.ts");

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

    let rendered = "";
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
        ui: {
          custom: async (factory: any) => {
            let selected: number | undefined;
            const component = factory(
              { requestRender() {} },
              {
                fg: (_name: string, value: string) => value,
                bold: (value: string) => value,
              },
              {},
              (value: number | undefined) => {
                selected = value;
              },
            );
            rendered = component.render(60).join("\n");
            component.handleInput("enter");
            return selected;
          },
        },
      },
    );

    expect(rendered).toContain("1. Yes");
    expect(rendered).toContain("2. No");
    expect(result.details.answers[0].answers).toEqual([
      { label: "Yes", value: "yes", source: "option" },
    ]);
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
          editor: async (_title: string, value: string) => {
            prompt = value;
            return "1,2";
          },
        },
      },
    );

    expect(prompt).toContain("1. Yes");
    expect(prompt).toContain("2. No");
    expect(
      prompt.split("\n").filter((line) => line.includes("word")),
    ).toHaveLength(8);
    expect(result.details.answers[0].answers).toEqual([
      { label: "Yes", value: "yes", source: "option" },
      { label: "No", value: "no", source: "option" },
    ]);
  });
});

describe("parseMultiSelect", () => {
  it("parses single numeric index", () => {
    expect(parseMultiSelect("1", OPTIONS)).toEqual([
      { label: "Alpha", value: "alpha", source: "option" },
    ]);
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
