# Playwright Runtime Reference

Runtime-only patterns for `browser-automation` when it uses this Playwright
helper. This is not a Playwright tutorial. For full API details, use the
official Playwright docs:

- Locators: https://playwright.dev/docs/locators
- Auto-waiting: https://playwright.dev/docs/actionability
- Screenshots: https://playwright.dev/docs/screenshots
- Network: https://playwright.dev/docs/network
- Emulation: https://playwright.dev/docs/emulation
- Authentication state: https://playwright.dev/docs/auth

## Runner contract

`node scripts/run.js`:

- preserves the caller working directory
- resolves input file paths before execution
- keeps runner logs on stderr
- supports `--quiet` and `--json` for clean script stdout
- exposes `chromium`, `firefox`, `webkit`, `devices`, `helpers`, and
  `getContextOptionsWithHeaders(opts)` as globals for every script
- still allows normal `require("fs")`, `require("path")`, and
  `require("playwright")`
- writes no temp execution files into the skill directory

## Script skeleton

Use this shape for generated scripts. Keep generated scripts and artifacts under
`/tmp/playwright-*` unless the user asked for permanent tests.

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

## Turnkey screenshots

Use these before writing custom batch scripts.

```bash
node scripts/screenshot-url.js \
  --url http://localhost:3000/settings \
  --selector main \
  --out /tmp/playwright-settings.png \
  --json
```

```bash
node scripts/screenshot-sequence.js \
  --url-template 'http://localhost:3030/{n}?clicks=20' \
  --from 1 \
  --to 17 \
  --selector .slidev-page \
  --out-dir /tmp/playwright-slidev \
  --json
```

Useful flags: `--viewport 1280x720`, `--title-selector h1`,
`--manifest /tmp/manifest.json`, `--viewport-only`, `--headed`,
`--step -1`, `--continue-on-error`.

## Locator priority

Prefer stable, user-facing locators:

1. `getByRole`, `getByLabel`, `getByPlaceholder`
2. Unique text with `getByText`
3. Stable test ids or data attributes
4. Semantic CSS selectors
5. XPath or layout-dependent CSS only as a last resort

## Waiting

Use Playwright auto-waiting and explicit state waits. Do not add fixed sleeps
unless validating time-based behavior.

```javascript
await page.getByRole("button", { name: "Save" }).click();
await page.waitForURL("**/success");
await page.locator(".spinner").waitFor({ state: "hidden" });
```

For SPA screenshots, use rendered-state readiness:

```javascript
await page.goto(TARGET_URL, { waitUntil: "domcontentloaded" });
await helpers.waitForStablePage(page, {
  selector: ".slidev-page",
  animationFrames: 2,
});
```

`networkidle` can be insufficient or too strict for SPAs. Prefer a selector that
proves the target UI rendered.

## Network interception

Use route interception only when the task requires mocked or inspected traffic.

```javascript
await page.route("**/api/users", (route) => {
  route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify([{ id: 1, name: "Test User" }]),
  });
});
```

## Mobile emulation

```javascript
const iPhone = devices["iPhone 12"];
const context = await browser.newContext(
  getContextOptionsWithHeaders({ ...iPhone }),
);
```

## Custom headers

Use the environment variables documented in `../SKILL.md`. With raw contexts,
wrap options with `getContextOptionsWithHeaders(...)`.

```javascript
const context = await browser.newContext(
  getContextOptionsWithHeaders({ viewport: { width: 1280, height: 720 } }),
);
```

## Troubleshooting

- Element not found: check iframe boundaries, visibility, and locator
  uniqueness.
- Timeout: inspect page load state, network activity, and selector state before
  raising timeouts.
- JSON polluted: use `--json` or `--quiet`; runner logs go to stderr, but your
  script must also keep its own logs off stdout.
- Syntax error: fix the quoted failing line before rerunning.
- Missing browser package: use `setup.md`.
