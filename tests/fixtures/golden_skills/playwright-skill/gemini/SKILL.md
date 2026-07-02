---
description: Support-only Playwright runtime/reference for browser-automation — dev-server
  detection, a Node.js script runner, quiet screenshot helpers, SPA readiness helpers,
  and custom HTTP headers. Use when browser-automation selects the bundled Playwright
  fallback; do not route user intent here directly.
name: playwright-skill
---

# Playwright Support Runtime

Support-only helper for `browser-automation`. Provides Playwright primitives:
dev-server detection, a script runner (`scripts/run.js`), screenshot CLIs, and
helper utilities (`scripts/lib/helpers.js`).

Do not treat this as the user-facing browser skill. Load it only when
`browser-automation` chooses the bundled Playwright helper as the
runtime/reference.

## Critical workflow

1. **Run from this skill directory** — the directory containing this `SKILL.md`.
   If the loaded skill path is different from `~/.pi/agent/skills`, use that
   loaded path.

2. **Detect dev servers first** for localhost testing:

   ```bash
   node scripts/run.js --json "console.log(JSON.stringify(await helpers.detectDevServers()))"
   ```

   One server → use it. Multiple → ask which. None → ask for a URL.

3. **Use `/tmp/playwright-*` for generated scripts and artifacts** unless the
   user asked for permanent tests. Never write generated scripts or artifacts
   into `scripts/`, the skill directory, or the user's project.

4. **Prefer headless screenshots in Pi/headless harnesses.** Use headed mode
   only when the platform exposes a usable visible browser.

5. **Parameterize target URLs** at the top of generated scripts as `TARGET_URL`.

## Running scripts

```bash
node scripts/run.js --quiet /tmp/playwright-test-<name>.js
node scripts/run.js --json "console.log(JSON.stringify({ ok: !!chromium }))"
```

`run.js` preserves the caller working directory, auto-wraps code for `await`,
auto-installs Playwright on first run using bun with npm fallback, and sends
runner logs to stderr. Script stdout stays clean for JSON.

`chromium`, `firefox`, `webkit`, `devices`, `helpers`, and
`getContextOptionsWithHeaders(opts)` are exposed as globals for all scripts.
Scripts may still use normal imports such as `require("fs")`, `require("path")`,
or `require("playwright")`.

## Turnkey screenshots

For one page:

```bash
node scripts/screenshot-url.js \
  --url http://localhost:3030/1?clicks=20 \
  --selector .slidev-page \
  --out /tmp/playwright-slide-01.png \
  --manifest /tmp/playwright-slide-01.json \
  --json
```

For a sequence:

```bash
node scripts/screenshot-sequence.js \
  --url-template 'http://localhost:3030/{n}?clicks=20' \
  --from 1 \
  --to 17 \
  --selector .slidev-page \
  --out-dir /tmp/playwright-slidev \
  --manifest /tmp/playwright-slidev/manifest.json \
  --json
```

The manifest includes URL, title, screenshot path, viewport, console errors,
network failures, and HTTP responses with status >=400.

## Helpers

Open `scripts/lib/helpers.js` when you need helper signatures. Key helpers:
`launchBrowser`, `createContext`, `waitForStablePage`, `waitForPageReady`,
`safeClick`, `safeType`, `takeScreenshot`, `authenticate`, and
`detectDevServers`.

Use `helpers.waitForStablePage(page, { selector, animationFrames })` before SPA
screenshots when `networkidle` is not enough.

## Custom HTTP headers

Set env vars before invoking `run.js` or screenshot helpers to inject extra
headers into every request:

```bash
# single header
PW_HEADER_NAME=X-Automated-By PW_HEADER_VALUE=playwright-skill \
  node scripts/run.js /tmp/script.js

# multiple
PW_EXTRA_HEADERS='{"X-Automated-By":"playwright-skill","X-Debug":"true"}' \
  node scripts/run.js /tmp/script.js
```

Headers apply automatically when scripts use `helpers.createContext(browser)`.
For raw `browser.newContext(...)`, wrap options with
`getContextOptionsWithHeaders(...)`.

## Output

```text
URL: <target URL>
Actions: <actions run>
Artifacts: <paths or none>
Failures: <failures or none>
```

Base success claims on script output or artifacts, not on command completion alone.

## Failure handling

- `run.js` not found: run from the directory containing this `SKILL.md`, or use
  the absolute loaded skill path.
- Dev server not detected: ask the user for the URL rather than assuming
  localhost:3000.
- Script syntax error: quote the failing line, state the cause, rewrite the
  offending section — do not re-run the broken script.
- Playwright not installed: `run.js` and screenshot helpers auto-install on
  first run; if that fails, use `references/setup.md`.

## References

- [`references/setup.md`](references/setup.md) — first-time install (bun
  preferred, npm fallback).
- [`references/api.md`](references/api.md) — runtime-only patterns and links to
  official Playwright API docs. Open it when a helper doesn't cover the needed
  action (custom locators, waits, network interception, or auth patterns).
