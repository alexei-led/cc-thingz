import { describe, expect, it } from "bun:test";

import {
  parsePackageContribution,
  validatePackageCommand,
} from "../../../src/plugins/pi/extensions/extensions/hook-runner/config.ts";

describe("parsePackageContribution", () => {
  it("returns undefined for invalid JSON", () => {
    expect(parsePackageContribution("{ not valid")).toBeUndefined();
  });

  it("returns undefined when cc-thingz field absent", () => {
    expect(
      parsePackageContribution(
        JSON.stringify({ name: "pkg", version: "1.0.0" }),
      ),
    ).toBeUndefined();
  });

  it("returns undefined when cc-thingz.hooks absent", () => {
    expect(
      parsePackageContribution(JSON.stringify({ "cc-thingz": {} })),
    ).toBeUndefined();
  });

  it("returns undefined when cc-thingz.hooks is not an object", () => {
    expect(
      parsePackageContribution(JSON.stringify({ "cc-thingz": { hooks: [] } })),
    ).toBeUndefined();
  });

  it("parses a valid contribution", () => {
    const content = JSON.stringify({
      name: "acme",
      "cc-thingz": {
        hooks: {
          PostToolUse: [
            {
              matcher: "Write",
              hooks: [
                { type: "command", command: "/usr/local/bin/acme-audit" },
              ],
            },
          ],
        },
      },
    });
    const result = parsePackageContribution(content);
    expect(result?.PostToolUse).toBeDefined();
    expect(result?.PostToolUse?.[0].matcher).toBe("Write");
    expect(result?.PostToolUse?.[0].hooks[0].config.command).toBe(
      "/usr/local/bin/acme-audit",
    );
  });

  it("drops malformed entries inside an otherwise-valid contribution", () => {
    const content = JSON.stringify({
      "cc-thingz": {
        hooks: {
          PreToolUse: [
            { matcher: "Bash", hooks: [{ type: "command" }] }, // missing command
            {
              matcher: "Read",
              hooks: [{ type: "command", command: "/bin/ok" }],
            },
          ],
        },
      },
    });
    const result = parsePackageContribution(content);
    expect(result?.PreToolUse).toBeDefined();
    expect(result?.PreToolUse?.length).toBe(1);
    expect(result?.PreToolUse?.[0].hooks[0].config.command).toBe("/bin/ok");
  });

  it("ignores entries whose hooks list is empty after filtering", () => {
    const content = JSON.stringify({
      "cc-thingz": {
        hooks: {
          PreToolUse: [{ matcher: "Bash", hooks: [{ type: "command" }] }], // command missing → entry dropped
        },
      },
    });
    const result = parsePackageContribution(content);
    // All groups dropped → event entry not present
    expect(result?.PreToolUse).toBeUndefined();
  });
});

// ---------------------------------------------------------------------------
// validatePackageCommand — package-contributed commands must not escape repoDir
// nor smuggle shell metacharacters past `bash -c`.
// ---------------------------------------------------------------------------

describe("validatePackageCommand", () => {
  const repoDir = "/Users/dev/.pi/agent/git/github.com/acme/plugin";

  it("accepts an absolute path inside repoDir", () => {
    expect(validatePackageCommand(`${repoDir}/hooks/audit.sh`, repoDir)).toBe(
      `${repoDir}/hooks/audit.sh`,
    );
  });

  it("substitutes ${PKG_DIR} with repoDir", () => {
    expect(validatePackageCommand("${PKG_DIR}/hooks/audit.sh", repoDir)).toBe(
      `${repoDir}/hooks/audit.sh`,
    );
  });

  it("rejects relative paths", () => {
    expect(validatePackageCommand("./audit.sh", repoDir)).toBeUndefined();
    expect(validatePackageCommand("audit.sh", repoDir)).toBeUndefined();
  });

  it("rejects paths outside repoDir", () => {
    expect(validatePackageCommand("/bin/rm", repoDir)).toBeUndefined();
    expect(validatePackageCommand("/etc/passwd", repoDir)).toBeUndefined();
  });

  it("rejects path-traversal attempts", () => {
    expect(
      validatePackageCommand(`${repoDir}/../../../bin/rm`, repoDir),
    ).toBeUndefined();
  });

  // One assertion per forbidden character. `bash -c` interprets all of these,
  // so the validator must reject the command even when the leading path looks
  // safe. Newline/CR are included because bash executes each line separately.
  const FORBIDDEN_CHARS: ReadonlyArray<readonly [string, string]> = [
    ["semicolon", ";"],
    ["ampersand", "&"],
    ["pipe", "|"],
    ["less-than", "<"],
    ["greater-than", ">"],
    ["backtick", "`"],
    ["dollar-sign", "$"],
    ["open-paren", "("],
    ["close-paren", ")"],
    ["backslash", "\\"],
    ["open-brace", "{"],
    ["close-brace", "}"],
    ["newline", "\n"],
    ["carriage-return", "\r"],
  ];

  it.each(FORBIDDEN_CHARS)(
    "rejects shell metacharacter %s (%j)",
    (_label, ch) => {
      expect(
        validatePackageCommand(`${repoDir}/safe.sh${ch}injected`, repoDir),
      ).toBeUndefined();
    },
  );

  it("rejects empty / whitespace-only commands", () => {
    expect(validatePackageCommand("", repoDir)).toBeUndefined();
    expect(validatePackageCommand("   ", repoDir)).toBeUndefined();
  });

  it("accepts safe args after the executable path", () => {
    // Arguments without forbidden metachars pass through unchanged.
    expect(
      validatePackageCommand(
        `${repoDir}/hooks/audit.sh --verbose log.txt`,
        repoDir,
      ),
    ).toBe(`${repoDir}/hooks/audit.sh --verbose log.txt`);
  });
});

describe("parsePackageContribution with repoDir", () => {
  const repoDir = "/pkg/root";

  it("drops malicious hook commands and keeps safe ones", () => {
    const content = JSON.stringify({
      "cc-thingz": {
        hooks: {
          PreToolUse: [
            {
              matcher: "Bash",
              hooks: [
                { type: "command", command: "rm -rf ~" }, // not absolute
                { type: "command", command: `${repoDir}/scripts/safe.sh` }, // safe, inside repo
                {
                  type: "command",
                  command: `${repoDir}/scripts/safe.sh; curl evil`,
                }, // metachar
              ],
            },
          ],
        },
      },
    });
    const result = parsePackageContribution(content, repoDir);
    expect(result?.PreToolUse).toBeDefined();
    expect(result?.PreToolUse?.length).toBe(1);
    expect(result?.PreToolUse?.[0].hooks.length).toBe(1);
    expect(result?.PreToolUse?.[0].hooks[0].config.command).toBe(
      `${repoDir}/scripts/safe.sh`,
    );
  });

  it("returns undefined when every contributed command is rejected", () => {
    const content = JSON.stringify({
      "cc-thingz": {
        hooks: {
          PostToolUse: [
            { matcher: "*", hooks: [{ type: "command", command: "/bin/rm" }] },
          ],
        },
      },
    });
    expect(parsePackageContribution(content, repoDir)).toBeUndefined();
  });
});
