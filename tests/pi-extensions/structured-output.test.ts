import { afterEach, describe, expect, it, mock } from "bun:test";
import structuredOutput from "../../src/plugins/pi/extensions/extensions/structured-output.ts";

const originalOptIn = process.env.CC_THINGZ_STRUCTURED_OUTPUT;

afterEach(() => {
	if (originalOptIn === undefined) delete process.env.CC_THINGZ_STRUCTURED_OUTPUT;
	else process.env.CC_THINGZ_STRUCTURED_OUTPUT = originalOptIn;
});

describe("structured-output opt-in", () => {
	it.each([undefined, "", "0", "true"])("does not register the demonstration tool for %j", (value) => {
		if (value === undefined) delete process.env.CC_THINGZ_STRUCTURED_OUTPUT;
		else process.env.CC_THINGZ_STRUCTURED_OUTPUT = value;
		const registerTool = mock();
		structuredOutput({ registerTool });
		expect(registerTool).not.toHaveBeenCalled();
	});

	it("registers the fixed-schema tool only with explicit opt-in", () => {
		process.env.CC_THINGZ_STRUCTURED_OUTPUT = "1";
		const registerTool = mock();
		structuredOutput({ registerTool });
		expect(registerTool).toHaveBeenCalledTimes(1);
		expect(registerTool.mock.calls[0][0]).toMatchObject({ name: "structured_output" });
	});
});
