---
description: 'Browser automation for rendered UI exploration, validation, screenshots,
  recordings, and end-to-end flows. Use when a task needs an actual browser or rendered
  DOM: inspect UI state, click/fill forms, debug frontend behavior, capture evidence,
  verify a feature, or run/generate browser tests. NOT for API checks or pure logic
  tests where curl, unit tests, or JSDOM is cheaper.'
name: browser-automation
---

# Browser Automation

Use a real browser only when rendered behavior matters: UI state, navigation,
forms, auth, screenshots, recordings, accessibility, visual checks, or
end-to-end flows.

Keep automation temporary unless the user asks for permanent tests. Do not use a
browser for plain HTTP API checks or pure logic tests.

## Runtime Selection

1. Prefer a platform built-in browser tool when available in the active tool
   list. See [`references/platform-browser-tools.md`](references/platform-browser-tools.md).
2. Use the project's configured browser runner when it exists.
3. Use `playwright-skill` only as the bundled fallback/runtime reference.
4. If no runtime is available, report blocked with the missing tool/package.

Use the cheapest runtime that proves the claim.

## Workflow

1. Define the goal: explore, validate, screenshot, record, debug, or test.
2. Read needed local context: start scripts, browser config, routes, fixtures,
   seed/reset docs, and auth notes.
3. Detect or start the dev server. Reuse a reachable server.
4. Use deterministic data: seeded users, fixed dates, stable IDs, reset state,
   and mocked external services.
5. Drive with semantic targets first: role, label, text, test id; CSS last.
6. Capture artifacts needed to support the result: screenshot, trace, console
   errors, network failures, accessibility snapshot, manifest, or report.
7. Prefer screenshot/manifest evidence for visual checks in headless harnesses.
8. Report pass, fail, or blocked. Do not imply success if the check did not run.

## Playwright Fallback

Use Playwright when no built-in browser tool exists, the project already uses
Playwright, or a repeatable script/test is the best artifact.

If using the bundled helper, load `playwright-skill` for exact setup and
invocation. Use its turnkey screenshot helpers before writing custom batch
scripts:

```bash
node scripts/screenshot-url.js --url <url> --selector <ready-selector> --json
node scripts/screenshot-sequence.js --url-template '<url/{n}>' --from 1 --to 10 --json
```

Do not write generated files into the helper directory or project unless
creating permanent tests was requested.

## Script and Test Rules

- Write temporary scripts to `/tmp/playwright-<name>.js` or
  `/tmp/playwright-<name>.spec.ts` when using the Playwright fallback.
- Never use fixed sleep delays.
- Wait or assert on visible state, URL, selector, network state, or
  accessibility snapshot.
- Prefer headed mode only when the platform exposes a usable visible browser.
  In Pi or other headless harnesses, use headless screenshots plus manifests as
  visual evidence.
- Keep credentials, production data, and destructive actions out of browser
  automation unless the user explicitly approves.

## Failure Handling

- No target URL: detect a local dev server; ask if none is found.
- Multiple reachable servers: ask which target to use.
- Missing auth or fixture data: ask for safe test credentials or report blocked.
- Runtime unavailable: report the missing tool/package and required enablement.
- Fix or re-run only when fixing is in scope.
- Failure after two scoped attempts: save evidence, quote the failing line or UI
  state, and stop.

## Output Contract

```markdown
## Browser Automation Result

Target: <page, feature, or flow>
Runtime: <built-in browser | project runner | playwright-skill | blocked>
Actions: <commands or browser action summary>
Result: <pass | fail | blocked>
Evidence: <screenshot/trace/output path or key observation>
Next Fix: <only when failing or blocked>
```