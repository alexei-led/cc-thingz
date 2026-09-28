# Bundled Playwright Scripts

Read this when browser-automation falls back to the scripts in `scripts/`:
runtime setup, the runner contract, a script skeleton, helpers, screenshot
flags, and custom headers. For the Playwright API itself, use the official docs:
[locators](https://playwright.dev/docs/locators),
[auto-waiting](https://playwright.dev/docs/actionability),
[network](https://playwright.dev/docs/network),
[emulation](https://playwright.dev/docs/emulation),
[authentication](https://playwright.dev/docs/auth).

The scripts derive from lackeyjb's playwright-skill, MIT License.

`<skill-dir>` below is the directory that contains the browser-automation
`SKILL.md`. Run every command from the caller's working directory.

## Runtime setup

- Requires Node.js 22+ and npm.
- The runner uses the caller project's Playwright package first, keeping that
  project's version. Otherwise it installs exactly Playwright 1.63.0 into
  `$XDG_CACHE_HOME/cc-thingz/playwright/1.63.0` (default `~/.cache`), never
  into the skill directory.
- Browser binaries are a separate install and may need network access:

  ```bash
  node <skill-dir>/scripts/setup-runtime.js chromium
  node <skill-dir>/scripts/setup-runtime.js firefox webkit
  ```

- A missing-browser error prints the matching Playwright CLI install command;
  use it so binaries match the package version.
- A successful package import does not prove the browser launches. Verify with
  a screenshot of `https://example.com` and check the manifest.
- Chromium sandboxing stays on. Set `PLAYWRIGHT_SKILL_NO_SANDBOX=1` only when the
  environment requires it and the trust boundary permits it.

## Dev server detection

```bash
node <skill-dir>/scripts/run.js --json \
  "console.log(JSON.stringify(await helpers.detectDevServers()))"
```

## Runner contract

`node <skill-dir>/scripts/run.js [--quiet|--json] <file | inline code>`, or code
on stdin:

- Keeps the caller's working directory and resolves input paths before running.
- Wraps code so top-level `await` works.
- Writes status logs to stderr. `--quiet` and `--json` also silence the
  first-run Playwright install, which otherwise writes to stdout. The script
  must keep its own logs off stdout too.
- Exposes `chromium`, `firefox`, `webkit`, `devices`, `helpers`, and
  `getContextOptionsWithHeaders(opts)` as globals, alongside normal
  `require("fs")`, `require("path")`, or `require("playwright")`.
- Writes no temporary files into the skill directory.

## Script skeleton

```javascript
const TARGET_URL = process.env.TARGET_URL || "http://localhost:3000";
const SCREENSHOT = "/tmp/playwright-check.png";

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext(getContextOptionsWithHeaders());
const page = await context.newPage();

try {
  await page.goto(TARGET_URL, { waitUntil: "domcontentloaded" });
  await helpers.waitForStablePage(page, { selector: "main" });

  // user flow here

  await page.screenshot({ path: SCREENSHOT, fullPage: true });
  console.log(JSON.stringify({ screenshot: SCREENSHOT }));
} finally {
  await browser.close();
}
```

`networkidle` can be too weak or too strict for SPAs. Wait for a selector that
proves the target UI rendered; `helpers.waitForStablePage(page, { selector,
animationFrames })` also waits for fonts and animation frames.

## Helpers

Signatures are in `scripts/lib/helpers.js`. Main ones: `launchBrowser`,
`createContext`, `waitForStablePage`, `waitForPageReady`, `safeClick`,
`safeType`, `takeScreenshot`, `authenticate`, and `detectDevServers`.

## Screenshot flags

Both screenshot scripts accept `--selector`, `--out` or `--out-dir`,
`--manifest`, `--json`, `--viewport 1280x720`, `--title-selector h1`,
`--viewport-only`, and `--headed`. `screenshot-sequence.js` adds
`--url-template` with `{n}`, `--from`, `--to`, `--step -1`, and
`--continue-on-error`.

## Custom headers

Set these before running `run.js` or a screenshot script to add headers to
every request:

```bash
PW_HEADER_NAME=X-Automated-By PW_HEADER_VALUE=browser-automation \
  node <skill-dir>/scripts/run.js /tmp/playwright-check.js
PW_EXTRA_HEADERS='{"X-Automated-By":"browser-automation","X-Debug":"true"}' \
  node <skill-dir>/scripts/run.js /tmp/playwright-check.js
```

`helpers.createContext(browser)` applies them. For a raw
`browser.newContext(...)`, wrap the options with
`getContextOptionsWithHeaders(...)`.

## Troubleshooting

- `run.js` not found: use the absolute `<skill-dir>` path.
- Element not found: check iframes, visibility, and locator uniqueness.
- Timeout: inspect load state, network activity, and selector state before
  raising timeouts.
- Syntax error: quote the failing line and fix that section before rerunning.
