const { execFileSync } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");

const SCRIPT_DIR = path.resolve(__dirname, "..");
const PLAYWRIGHT_VERSION = "1.57.0";

function log(options, ...parts) {
  if (!options?.quiet) console.error(...parts);
}

function cacheDirectory(options = {}) {
  return options.cacheDir || path.join(
    process.env.XDG_CACHE_HOME || path.join(os.homedir(), ".cache"),
    "cc-thingz", "playwright", PLAYWRIGHT_VERSION,
  );
}

function resolvePlaywright(options = {}) {
  const projectDir = options.projectDir || process.cwd();
  const candidates = [() => require.resolve("playwright", { paths: [projectDir] }),
    () => require.resolve("playwright", { paths: [require.resolve("@playwright/test", { paths: [projectDir] })] }),
    () => require.resolve(path.join(cacheDirectory(options), "node_modules", "playwright"))];
  for (const resolve of candidates) {
    try {
      return resolve();
    } catch (error) {
      if (error.code !== "MODULE_NOT_FOUND") throw error;
    }
  }
  return null;
}

function isPlaywrightInstalled(options = {}) {
  return resolvePlaywright(options) !== null;
}

function ensurePlaywrightInstalled(options = {}) {
  if (isPlaywrightInstalled(options)) return;
  const cacheDir = cacheDirectory(options);
  fs.mkdirSync(cacheDir, { recursive: true });
  log(options, `Installing Playwright ${PLAYWRIGHT_VERSION} in ${cacheDir}`);
  execFileSync("npm", [
    "install", "--prefix", cacheDir, "--no-save", "--package-lock=false",
    "--ignore-scripts", `playwright@${PLAYWRIGHT_VERSION}`,
  ], { cwd: cacheDir, stdio: options.quiet ? "ignore" : "inherit" });
  if (!isPlaywrightInstalled(options)) throw new Error("Playwright installation failed");
}

function loadPlaywright(options = {}) {
  ensurePlaywrightInstalled(options);
  return require(resolvePlaywright(options));
}

function ensureBrowserAvailable(browser, browserName, options = {}) {
  if (!fs.existsSync(browser.executablePath())) {
    const entry = resolvePlaywright(options);
    const cli = path.join(path.dirname(entry), "cli.js");
    throw new Error(`Playwright package is ready but ${browserName} is missing. Install it with: node ${JSON.stringify(cli)} install ${browserName}`);
  }
}

function sandboxOptions() {
  return process.env.PLAYWRIGHT_SKILL_NO_SANDBOX === "1"
    ? { chromiumSandbox: false, args: ["--no-sandbox", "--disable-setuid-sandbox"] }
    : { chromiumSandbox: true, args: [] };
}

module.exports = {
  SCRIPT_DIR,
  PLAYWRIGHT_VERSION,
  cacheDirectory,
  resolvePlaywright,
  ensurePlaywrightInstalled,
  isPlaywrightInstalled,
  loadPlaywright,
  ensureBrowserAvailable,
  sandboxOptions,
  log,
};
