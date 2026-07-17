#!/usr/bin/env node
/**
 * Playwright support-runtime executor.
 *
 * Executes Playwright automation code from:
 * - File path: node run.js script.js
 * - Inline code: node run.js 'await page.goto("...")'
 * - Stdin: cat script.js | node run.js
 *
 * The runner preserves the caller's working directory, keeps runner logs on
 * stderr, and exposes Playwright primitives as globals without blocking normal
 * require("fs"), require("path"), or require("playwright") usage.
 */

const fs = require("fs");
const os = require("os");
const path = require("path");
const Module = require("module");
const runtime = require("./lib/runtime");

const SCRIPT_DIR = __dirname;
const ORIGINAL_CWD = process.cwd();

function usage() {
  console.error(`Usage:
  node scripts/run.js [--quiet|--json] script.js
  node scripts/run.js [--quiet|--json] "await browser code"
  cat script.js | node scripts/run.js [--quiet|--json]

Options:
  --quiet, -q   suppress runner status logs; script stdout stays untouched
  --json        alias for --quiet, intended for scripts that print JSON
  --help, -h    show this help`);
}

function parseArgs(argv) {
  const options = { quiet: false, help: false };
  const input = [];

  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];

    if (arg === "--quiet" || arg === "-q") {
      options.quiet = true;
      continue;
    }

    if (arg === "--json") {
      options.quiet = true;
      continue;
    }

    if (arg === "--help" || arg === "-h") {
      options.help = true;
      continue;
    }

    if (arg === "--") {
      input.push(...argv.slice(i + 1));
      break;
    }

    input.push(arg);
  }

  return { options, input };
}

function log(options, ...parts) {
  if (!options.quiet) {
    console.error(...parts);
  }
}

function resolveFromCaller(inputPath) {
  if (path.isAbsolute(inputPath)) {
    return inputPath;
  }
  return path.resolve(ORIGINAL_CWD, inputPath);
}

function stripShebang(code) {
  return code.replace(/^#!.*(?:\r?\n|$)/, "");
}

function tempFilename(label) {
  const safeLabel = label.replace(/[^a-z0-9_-]/gi, "-").toLowerCase();
  return path.join(
    os.tmpdir(),
    `playwright-skill-${safeLabel}-${process.pid}-${Date.now()}.js`,
  );
}

function getCodeToExecute(input, options) {
  if (input.length > 0) {
    const candidate = resolveFromCaller(input[0]);
    if (fs.existsSync(candidate) && fs.statSync(candidate).isFile()) {
      log(options, `📄 Executing file: ${candidate}`);
      return {
        code: fs.readFileSync(candidate, "utf8"),
        filename: candidate,
        kind: "file",
      };
    }

    log(options, "⚡ Executing inline code");
    return {
      code: input.join(" "),
      filename: tempFilename("inline"),
      kind: "inline",
    };
  }

  if (!process.stdin.isTTY) {
    log(options, "📥 Reading from stdin");
    return {
      code: fs.readFileSync(0, "utf8"),
      filename: tempFilename("stdin"),
      kind: "stdin",
    };
  }

  usage();
  process.exit(1);
}

function getContextOptionsWithHeaders(helpers, options = {}) {
  return helpers.getContextOptionsWithHeaders(options);
}

function installRuntimeGlobals(playwright, helpers) {
  const globals = {
    playwright,
    chromium: playwright.chromium,
    firefox: playwright.firefox,
    webkit: playwright.webkit,
    devices: playwright.devices,
    helpers,
    getContextOptionsWithHeaders: (options = {}) =>
      getContextOptionsWithHeaders(helpers, options),
  };

  for (const [name, value] of Object.entries(globals)) {
    Object.defineProperty(globalThis, name, {
      configurable: true,
      enumerable: false,
      writable: true,
      value,
    });
  }
}

function wrapCode(code) {
  return `
module.exports = (async () => {
  try {
${stripShebang(code)}
  } catch (error) {
    console.error('❌ Automation error:', error.message);
    if (error.stack) {
      console.error(error.stack);
    }
    process.exitCode = 1;
  }
})();
`;
}

function createExecutionModule(filename) {
  const executionModule = new Module(filename, module.parent);
  executionModule.filename = filename;
  executionModule.paths = [
    ...Module._nodeModulePaths(path.dirname(filename)),
    ...Module._nodeModulePaths(SCRIPT_DIR),
  ];
  return executionModule;
}

async function executeCode(source) {
  const executionModule = createExecutionModule(source.filename);
  executionModule._compile(wrapCode(source.code), source.filename);

  if (
    executionModule.exports &&
    typeof executionModule.exports.then === "function"
  ) {
    await executionModule.exports;
  }
}

async function main() {
  const { options, input } = parseArgs(process.argv.slice(2));

  if (options.help) {
    usage();
    return;
  }

  process.env.PLAYWRIGHT_SKILL_QUIET = options.quiet ? "1" : "0";

  log(options, "🎭 Playwright Skill - Universal Executor");

  let playwright;
  try {
    playwright = runtime.loadPlaywright(options);
  } catch (error) {
    console.error("❌", error.message);
    process.exit(1);
  }

  const helpers = require("./lib/helpers");
  helpers.ensurePlaywrightReady({ quiet: options.quiet });
  installRuntimeGlobals(playwright, helpers);

  const source = getCodeToExecute(input, options);

  try {
    log(options, "🚀 Starting automation...");
    await executeCode(source);
  } catch (error) {
    console.error("❌ Execution failed:", error.message);
    if (error.stack) {
      console.error("\n📋 Stack trace:");
      console.error(error.stack);
    }
    process.exit(1);
  }
}

main().catch((error) => {
  console.error("❌ Fatal error:", error.message);
  process.exit(1);
});
