# TypeScript Testing

## Test Design

- Test behavior through public interfaces.
- Prefer integration-style tests when they give a stable signal.
- Mock only system boundaries: HTTP, time, randomness, filesystem, browser APIs, external services.
- Do not mock internal collaborators just to assert calls.
- Use red-green-refactor for risky changes: failing test, minimal fix, cleanup after green.
- Use `it.each` for input/output matrices and boundary cases.
- One test should prove one behavior. Multiple assertions are fine when they describe that behavior.
- Delete shallow or duplicate tests once deeper behavior tests cover the same path.

## Vitest

- Use type-safe Vitest mocks for external modules and standalone fakes.
- Match exact business values; use partial matchers only for generated or irrelevant fields.
- Reset only the mocks, timers, handlers, and globals a test changes.

## HTTP and External APIs

- Prefer msw or the project's HTTP test harness over mocking `fetch` directly.
- Test success, failure, empty, invalid, timeout, and cancellation paths when behavior changes.
- Assert returned `Result` variants or thrown Error subclasses directly.
- Avoid untyped `as Response` mocks; use real handlers or narrow helper factories.
- Include malformed JSON/schema tests for boundary validation code.

## React Tests

- Test user-visible behavior, not component internals.
- Query by role and accessible name first.
- Use `userEvent` for interactions.
- Cover affected loading, success, error, empty, disabled, and validation states.
- Do not keep tests that only prove a prop is rendered unless that is the behavior under change.

## Coverage and Waste

- Use coverage to find untested behavior, not to force meaningless assertions.
- Raise thresholds only when the suite already tests important paths.
- Remove tests that duplicate broader behavior tests, assert implementation details, or only lock trivial defaults.
- Prefer a missing edge-case test over another happy-path test.
