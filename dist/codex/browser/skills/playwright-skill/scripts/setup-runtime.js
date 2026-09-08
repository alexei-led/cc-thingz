const { execFileSync } = require("child_process");
const path = require("path");
const runtime = require("./lib/runtime");

const browsers = process.argv.slice(2);
if (browsers.some((name) => !["chromium", "firefox", "webkit"].includes(name))) {
  console.error("Usage: node setup-runtime.js [chromium firefox webkit]");
  process.exit(2);
}
runtime.ensurePlaywrightInstalled();
const cli = path.join(path.dirname(runtime.resolvePlaywright()), "cli.js");
execFileSync(process.execPath, [cli, "install", ...(browsers.length ? browsers : ["chromium"])], { stdio: "inherit" });
