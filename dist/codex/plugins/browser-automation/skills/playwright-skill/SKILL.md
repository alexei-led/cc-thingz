---
description: Support-only Playwright runtime/reference for browser-automation — dev-server
  detection, a Node.js script runner, and helpers for clicks, form fills, screenshots,
  multi-viewport, and custom HTTP headers. Use when browser-automation selects the
  bundled Playwright fallback; do not route user intent here directly.
name: playwright-skill
---

# Playwright Support Runtime

Support-only helper for `browser-automation`. Provides Playwright primitives: dev-server detection, a script runner (`scripts/run.js`), and helper utilities (`scripts/lib/helpers.js`).

Do not treat this as the user-facing browser skill. Load it only when `browser-automation` chooses the bundled Playwright helper as the runtime/reference.

## Critical workflow

1. **Detect dev servers first** for localhost testing:

   ```bash
   node -e "require('scripts/lib/helpers').detectDevServers().then(s => console.log(JSON.stringify(s)))"
   ```

   One server → use it. Multiple → ask which. None → ask for a URL.

2. **Write generated scripts to `/tmp/playwright-test-*.js`** — never into `scripts/` or the user's project.

3. **Visible browser by default** (`headless: false`). Headless only when the user asks.

4. **Parameterize the target URL** at the top of the script as `TARGET_URL`.

## Running scripts

```bash
node scripts/run.js /tmp/playwright-test-<name>.js   # file
node scripts/run.js "<code>"                          # inline
cat script.js | node scripts/run.js                   # stdin
```

`run.js` `cd`s to its own directory for module resolution, auto-wraps non-`async` code, and on first run auto-installs Playwright via bun. For code without `require()` it injects globals: `chromium`, `firefox`, `webkit`, `devices`, `helpers`, and `getContextOptionsWithHeaders(opts)`.

## Helpers

`scripts/lib/helpers.js` exports: `launchBrowser`, `createPage`, `createContext`, `waitForPageReady`, `safeClick`, `safeType`, `extractTexts`, `extractTableData`, `takeScreenshot`, `authenticate`, `scrollPage`, `handleCookieBanner`, `retryWithBackoff`, `detectDevServers`, `getExtraHeadersFromEnv`.

Open the file when you need a signature.

## Custom HTTP headers

Set env vars before invoking `run.js` to inject extra headers into every request:

```bash
# single header
PW_HEADER_NAME=X-Automated-By PW_HEADER_VALUE=playwright-skill \
  node scripts/run.js /tmp/script.js

# multiple
PW_EXTRA_HEADERS='{"X-Automated-By":"playwright-skill","X-Debug":"true"}' \
  node scripts/run.js /tmp/script.js
```

Headers apply automatically when scripts use `helpers.createContext(browser)`. For raw `browser.newContext(...)`, wrap options with `getContextOptionsWithHeaders(...)`.

## Failure handling

- `run.js` not found: check that `playwright-skill` dir is on the skill path; run from that directory explicitly.
- Dev server not detected: ask the user for the URL rather than assuming localhost:3000.
- Script syntax error: quote the failing line, state the cause, rewrite the offending section — do not re-run the broken script.
- Playwright not installed: `run.js` auto-installs on first run; if that fails, run `cd <skill-dir> && bun install` or `npm install`.

## References

- [`references/setup.md`](references/setup.md) — first-time install (bun preferred, npm fallback).
- [`references/api.md`](references/api.md) — selectors, locators, network interception, auth, visual regression, mobile emulation, performance, debugging, CI/CD.
