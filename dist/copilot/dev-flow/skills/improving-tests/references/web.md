# Browser and HTMX Tests

Use browser-automation for running flows interactively. If Playwright is not
configured, say so instead of guessing.

- `playwright test --list` is safe discovery; run browser tests only when needed. An empty list means no coverage, not unknown coverage.
- Locators: `getByRole`, then `getByLabel`, then `getByText`; `getByTestId` only when semantics cannot express it. No XPath, deep CSS, or generated IDs.
- Playwright auto-waits: assert with `expect(locator).toBeVisible()` instead of fixed timeouts.
- One user-visible flow per test. Delete page-load smoke tests once flow tests cover the page.
- HTMX: assert the swapped, added, or removed element, not internal events.
- Route-mock external services instead of calling them.
- Classify failures as locator, timing, app behavior, test logic, or environment.
