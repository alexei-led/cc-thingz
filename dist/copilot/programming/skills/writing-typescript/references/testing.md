# TypeScript Testing

## Style

- Use the project's runner and helpers. With Vitest, type mocks with `vi.mocked` and reset only the mocks, timers, and globals a test changes.
- HTTP: prefer the project's MSW or HTTP harness over mocking `fetch`. No untyped `as Response` mocks.
- Boundary validation code gets malformed-JSON and wrong-shape tests, plus timeout and cancellation cases when the code handles them.
- Replace real sleeps with fake timers, controlled promises, or poll-until helpers with hard timeouts.

## React

- Test user-visible behavior with Testing Library. Query by role and accessible name first; use `userEvent` when the project has it.
- Cover the loading, empty, error, disabled, and validation states the change touches.

## Fast Loop

- Run pure logic tests in the cheapest environment (`node`, not `jsdom` or a browser) unless behavior needs the DOM.
- Keep coverage, open-handle diagnostics, browser, and end-to-end runs off the hot path unless they are the task.
- Keep global setup and preload files small so focused runs stay focused.
- Tune worker counts only after measuring; transforms, DOM environments, and memory often make more workers slower.
