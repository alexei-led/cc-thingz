---
argument-hint: '[explore|verify|screenshot|record|test <target>]'
context: fork
description: 'Browser automation for rendered UI exploration, validation, screenshots,
  recordings, and end-to-end flows. Use when a task needs an actual browser or rendered
  DOM: inspect UI state, click/fill forms, debug frontend behavior, capture evidence,
  verify a feature, or run/generate browser tests. NOT for API checks or pure logic
  tests where curl, unit tests, or JSDOM is cheaper.'
name: browser-automation
user-invocable: true
---

# Browser Automation

Use this for browser exploration, validation, screenshots, recordings, frontend
debugging, accessibility checks, and E2E/user-flow testing. Do not delete,
reset, or mutate non-test data without explicit user confirmation.

If the app cannot be started, auth is missing, or fixtures are unavailable,
report BLOCKED instead of inventing passing results.

## Runtime Order

1. Use built-in browser tools first when they are visible in the current Claude
   Code session. If the user wants Claude in Chrome and no browser tools are
   visible, tell them to enable `claude-in-chrome` with `/mcp`.
2. Use the project's configured browser runner when it exists.
3. Use `playwright-skill` only as the bundled fallback/runtime reference.
4. If no runtime is available, report BLOCKED with the missing tool/package.

Use browser tools for rendered state: navigation, click/type/select, DOM or
accessibility snapshots, screenshots, console logs, network inspection, and
read-only page JavaScript. Use Bash for dev-server setup, project runners, and
repeatable tests.

## Arguments

- `explore <url|feature>` → inspect rendered page state
- `verify <feature>` → validate a feature in the browser
- `screenshot <url|feature>` → capture visual evidence
- `record <flow>` → record or script a manual browser session
- `test [target]` → run or generate browser/E2E tests
- empty → ask which browser task to run

If no argument is provided, ask one question:

- Action: What browser task should I run? Options: Explore, Verify, Screenshot,
  Record, Test.

## Prepare App and Data

Before any browser action, include dev-server detection/startup and safe test
data setup.

1. Detect the app start command from browser config, package scripts, Makefile,
   README, or existing docs.
2. If a running app is needed, check whether the configured `baseURL` or target
   URL is reachable. Start it only when the command is known.
3. Use deterministic fixtures: seeded users, fixed dates, stable IDs, reset
   database state, and mocked external services when needed.
4. Avoid production data, local user state, random order, wall-clock dependence,
   and previous-run state.

## Execute

### Built-in Browser Tools

When browser tools are visible, use them directly:

1. Navigate to the target URL.
2. Inspect snapshot/rendered state before interacting.
3. Click, type, select, or submit using accessible targets.
4. Capture artifacts needed to support the result.
5. Verify user-visible outcomes.

Use read-only page inspection JavaScript only for diagnosis. Do not mutate app
state through console scripts unless the user asked for that exact action.

### Project Browser Runner

Run the project's configured browser command. Infer the package manager from the
lockfile. Do not invent a runner.

### Playwright Helper Fallback

Load `playwright-skill` for exact helper setup and invocation. Write temporary
scripts to `/tmp/playwright-*.js`; never write generated files into the helper
directory or project unless permanent tests were requested.

## Browser Script Rules

- Prefer semantic locators: role, label, text, test id, CSS last.
- Never use fixed `waitForTimeout` delays.
- Use waits/assertions on visible UI state, URL, selector, network state, or
  accessibility snapshot.
- Prefer visible/headed mode for exploration and screenshots. Use headless for
  CI or when requested.
- Keep temporary scripts under `/tmp`.
- Keep permanent tests in the project's existing test layout only when the user
  asked to add tests.

## Debugging Failed Checks

1. Read the browser or runner error output.
2. Capture current rendered state with a snapshot or screenshot.
3. Check console logs and failed network requests.
4. Fix the test or app only if fixing is in scope.
5. Re-run the narrow check once.
6. If still failing after two attempts, save evidence and stop.

## HTMX and SPA Notes

- Verify DOM updates after swaps or client-side route changes.
- Test triggers, form submissions, partial updates, and history behavior.
- Assert user-visible changes rather than implementation internals.
- Check relevant response headers and network calls when diagnosing.

## Output

```markdown
## Browser Automation Result

Action: <explore | verify | screenshot | record | test>
Result: <PASS | FAIL | BLOCKED>
Runtime: <built-in browser | project runner | playwright-skill | unavailable>
Dev server: <reused | started | not needed | blocked: reason>
Fixtures/Auth: <deterministic setup summary or blocker>
Artifacts: <screenshot/trace/video/report/log paths or none>
Details: <key observations, commands, tool actions, or test results>
Next Fix: <only when failing or blocked>
```
