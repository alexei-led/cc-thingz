# TypeScript Testing

Use before adding or changing TypeScript tests. Follow the project's test runner and helpers. Keep the local test loop fast enough for repeated agent feedback.

## Test Design

- Test behavior through public interfaces.
- Prefer integration-style tests when they give a stable signal.
- Mock only system boundaries: HTTP, time, randomness, filesystem, browser APIs, external services.
- Do not mock internal collaborators just to assert calls.
- Use red-green-refactor for risky changes: write a failing test, make it pass, then clean up.
- Use the project's parameterized-test syntax for input/output matrices and boundary cases.
- One test should prove one behavior. Multiple assertions are fine when they describe that behavior.
- Delete shallow or duplicate tests once deeper behavior tests cover the same path.

## Fast feedback

- Keep coverage, open-handle diagnostics, browser tests, and end-to-end tests out of the hot path unless that mode is the task.
- Keep pure logic tests in the cheapest environment. Do not pay DOM or browser setup cost unless behavior needs it.
- Keep global setup, preload files, and shared test utilities small enough that focused runs stay focused.
- Tune workers only after measuring; too many workers can be slower when transforms, DOM environments, memory, or external services bottleneck.
- Replace real sleeps with fake timers, controlled promises, or poll-until-condition helpers with hard timeouts.

## Runner-Specific Mocks

- When using Vitest, use type-safe mocks for external modules and standalone fakes.
- Match exact business values; use partial matchers only for generated or irrelevant fields.
- Reset only the mocks, timers, handlers, and globals a test changes.

## HTTP and External APIs

- Prefer an existing MSW or project HTTP harness over mocking `fetch` directly.
- Test success, failure, empty, invalid, timeout, and cancellation paths when behavior changes.
- Assert returned `Result` variants or thrown Error subclasses when the code exposes those conventions.
- Avoid untyped `as Response` mocks; use real handlers or narrow helper factories.
- Include malformed JSON/schema tests for boundary validation code.

## React Tests

- Test user-visible behavior, not component internals.
- Query by role and accessible name first.
- Use `userEvent` when the project already uses Testing Library.
- Cover affected loading, success, error, empty, disabled, and validation states.
- Do not keep tests that only prove a prop is rendered unless that is the behavior under change.

## Coverage and Waste

- Use coverage to find untested behavior, not to force meaningless assertions.
- Keep coverage off the hot feedback path; run it in a coverage job or coverage-specific task.
- Raise thresholds only when the suite already tests important paths.
- Remove tests that duplicate broader behavior tests, assert implementation details, or only lock trivial defaults.
- Prefer a missing edge-case test over another happy-path test.
