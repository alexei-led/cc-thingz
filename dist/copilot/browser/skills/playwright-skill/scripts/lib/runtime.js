const { execSync } = require("child_process");
const path = require("path");

const SCRIPT_DIR = path.resolve(__dirname, "..");

function log(options, ...parts) {
  if (!options?.quiet) {
    console.error(...parts);
  }
}

function commandExists(command) {
  try {
    execSync(`command -v ${command}`, { stdio: "ignore" });
    return true;
  } catch (_error) {
    return false;
  }
}

function resolvePlaywright() {
  return require.resolve("playwright", { paths: [SCRIPT_DIR] });
}

function isPlaywrightInstalled() {
  try {
    resolvePlaywright();
    return true;
  } catch (_error) {
    return false;
  }
}

function runInstallCommands(name, commands, options) {
  log(options, `📦 Playwright not found. Installing with ${name}...`);
  const stdio = options?.quiet ? "ignore" : "inherit";

  for (const command of commands) {
    execSync(command, { cwd: SCRIPT_DIR, stdio });
  }
}

function ensurePlaywrightInstalled(options = {}) {
  if (isPlaywrightInstalled()) {
    return;
  }

  const attempts = [
    {
      name: "bun",
      available: commandExists("bun") && commandExists("bunx"),
      commands: ["bun install", "bunx playwright install chromium"],
    },
    {
      name: "npm",
      available: commandExists("npm") && commandExists("npx"),
      commands: ["npm install", "npx playwright install chromium"],
    },
  ];

  const errors = [];

  for (const attempt of attempts) {
    if (!attempt.available) {
      continue;
    }

    try {
      runInstallCommands(attempt.name, attempt.commands, options);
      if (isPlaywrightInstalled()) {
        log(options, "✅ Playwright installed successfully");
        return;
      }
    } catch (error) {
      errors.push(`${attempt.name}: ${error.message}`);
    }
  }

  const details = errors.length > 0 ? ` Attempts: ${errors.join("; ")}` : "";
  throw new Error(
    `Failed to install Playwright. Run manually: cd ${SCRIPT_DIR} && bun run setup.${details}`,
  );
}

function loadPlaywright(options = {}) {
  ensurePlaywrightInstalled(options);
  return require(resolvePlaywright());
}

module.exports = {
  SCRIPT_DIR,
  ensurePlaywrightInstalled,
  isPlaywrightInstalled,
  loadPlaywright,
  log,
};
