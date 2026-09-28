---
{"description":"Browser automation for rendered UI exploration, validation, screenshots, recordings, and end-to-end flows. Use when a task needs an actual browser or rendered DOM: inspect UI state, click/fill forms, debug frontend behavior, capture evidence, verify a feature, or run/generate browser tests. NOT for API checks or pure logic tests where curl, unit tests, or JSDOM is cheaper.","name":"browser-automation"}
---

# Browser Automation

Prove rendered behavior in a real browser and report pass, fail, or blocked with
evidence. Keep automation temporary unless the user asks for permanent tests.

## Runtime

Use the cheapest runtime that proves the claim:

1. Browser tools exposed in the current session. See
   [`references/platform-browser-tools.md`](references/platform-browser-tools.md).
2. The project's configured browser runner. Infer the package manager from the
   lockfile; do not invent a runner.
3. The bundled Playwright scripts in this skill's `scripts/` directory. Read
   [`references/playwright.md`](references/playwright.md) for setup, the script
   skeleton, helpers, and custom headers.
4. None available: report blocked and name the missing tool or package.

## Rules

- Target: reuse a reachable dev server; start one only when its command is
  known. Ask when no server or several servers are found.
- Data: use seeded users, fixed dates, reset state, and mocked external
  services. Credentials, production data, and destructive actions need explicit
  user approval.
- Locators: role, label, text, or test id first; CSS last.
- Waiting: wait on observable state such as a selector, URL, network response,
  or accessibility snapshot. Never add fixed sleeps. For SPA or HTMX pages,
  assert the DOM after swaps and client-side route changes.
- Headless: when the platform exposes no visible browser (Pi, CI, most CLIs),
  use headless screenshots plus a manifest as visual evidence. Use headed mode
  only when the user can see the browser.
- Files: write generated scripts and artifacts to `/tmp/playwright-*`. Write to
  the project only when the user asked for permanent tests, and never write into
  the skill directory.
- Failures: fix the app or tests only when that is in scope. After two failed
  scoped attempts, save evidence, quote the failing line or UI state, and stop.
- Permanent tests: done when the relevant build/test/lint checks pass on what
  you changed, or you name each check that did not run and why.

## Bundled Playwright scripts

Run them by absolute path from the caller's working directory, where
`<skill-dir>` is the directory that contains this `SKILL.md`. Prefer the
screenshot scripts over custom batch scripts:

```bash
node <skill-dir>/scripts/screenshot-url.js --url <url> --selector <ready-selector> \
  --out /tmp/playwright-page.png --json
node <skill-dir>/scripts/screenshot-sequence.js --url-template '<url/{n}>' --from 1 --to 10 \
  --selector <ready-selector> --out-dir /tmp/playwright-shots --json
node <skill-dir>/scripts/run.js --json /tmp/playwright-check.js
```

- Manifests record URL, title, screenshot path, viewport, console errors,
  network failures, and HTTP responses with status >=400.
- `run.js` keeps the caller's working directory. `--json` or `--quiet` sends
  runner logs to stderr, so stdout carries only the script's JSON. Playwright
  globals such as `chromium` and `helpers` stay available when the script also
  uses `require("fs")` or `require("path")`.

## Platform additions

No target-specific additions.

## Output

```markdown
## Browser Automation Result

Target: <page, feature, or flow>
Runtime: <built-in browser | project runner | bundled Playwright | blocked>
Actions: <commands or browser actions>
Result: <pass | fail | blocked>
Evidence: <screenshot, manifest, or trace paths, or the key observation>
Next fix: <only when failing or blocked>
```

Report blocked, not pass, when the check did not run.
