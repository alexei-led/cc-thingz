# Web Test Slice

Use this only for browser, Playwright, HTMX, or DOM-flow test work. The host skill
owns scope, workflow, and output.

## Commands

Use project commands first. If Playwright is configured, safe discovery commands include:

```bash
npx playwright test --list
bunx playwright test --list
```

Run browser tests only when explicitly needed or requested:

```bash
npx playwright test --reporter=list
bunx playwright test --reporter=list
```

If Playwright is not configured, say so instead of guessing.

## Locator strategy

Prefer:

1. `getByRole()`
2. `getByLabel()`
3. `getByText()`
4. `getByTestId()` only when semantic queries cannot express the behavior

Avoid XPath, deep CSS selectors, generated IDs, and sleeps.

## Flow quality

- Test one user-visible flow per test.
- Use descriptive names.
- Prefer assertions that prove the user-visible outcome.
- Delete tests that only prove a page loads when stronger flow tests exist.
- For HTMX, assert the partial update or removed/added element, not internal events.

## Waiting

Playwright auto-waits. Prefer assertions such as `expect(locator).toBeVisible()`
or `not.toBeVisible()` over fixed timeouts.

## Review focus

Flag:

- brittle selectors
- fixed sleeps
- tests with no assertions
- duplicate page-load smoke tests
- missing loading, error, empty, permission, or validation states
- tests that require real external services when a fixture or route mock would suffice

## Failure handling

- If tests fail, quote output and classify likely cause: locator, timing, app behavior, test logic, or environment.
- If `--list` returns no tests, report that and do not infer coverage.
- If no issues are found, say so; do not invent findings.
