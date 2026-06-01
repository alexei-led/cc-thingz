# TypeScript Testing

Use this reference before adding or changing TypeScript tests.

## Test Design

- Test behavior through public interfaces.
- Prefer integration-style tests when they give a stable signal.
- Mock only system boundaries: HTTP, time, randomness, filesystem, browser APIs, external services.
- Do not mock internal collaborators just to assert calls.
- Use red-green-refactor for risky changes: failing test, minimal fix, cleanup after green.
- Delete shallow or duplicate tests once deeper behavior tests cover the same path.
- One test should prove one behavior. Multiple assertions are fine when they describe that behavior.
- Use `it.each` for input/output matrices and boundary cases.

```typescript
describe("validateEmail", () => {
  it.each([
    { input: "user@example.com", expected: true },
    { input: "", expected: false },
    { input: "invalid", expected: false },
  ])("returns $expected for $input", ({ input, expected }) => {
    expect(validateEmail(input)).toBe(expected);
  });
});
```

## Vitest

- Use `vi.fn` for standalone fakes.
- Use `vi.spyOn` sparingly and restore it after the test.
- Use `vi.mock` at top level for imported external modules.
- Use `vi.mocked` for type-safe access to mocked functions.
- Match exact business values; use partial matchers only for generated or irrelevant fields.
- Reset server handlers, timers, and spies that a test changes. Do not add global cleanup that hides test coupling.

```typescript
import { afterEach, describe, expect, it, vi } from "vitest";

afterEach(() => {
  vi.restoreAllMocks();
});
```

## HTTP and External APIs

Prefer msw or the project's HTTP test harness over mocking `fetch` directly.

```typescript
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";

const server = setupServer(
  http.get("/api/users/:id", ({ params }) => {
    return HttpResponse.json({ id: params.id, email: "user@example.com" });
  }),
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

## Async and Error Paths

- Test success, failure, empty, invalid, timeout, and cancellation paths when behavior changes.
- Assert returned `Result` variants or thrown typed errors directly.
- Avoid untyped `as Response` mocks; use real handlers or narrow helper factories.

```typescript
describe("fetchUser", () => {
  it("returns invalid-response for malformed JSON", async () => {
    server.use(
      http.get("/api/users/:id", () => HttpResponse.json({ id: 123 })),
    );

    await expect(fetchUser("123")).resolves.toEqual({
      ok: false,
      error: "invalid-response",
    });
  });
});
```

## React Tests

- Test user-visible behavior, not component internals.
- Query by role and accessible name first.
- Use `userEvent` for interactions.
- Cover affected loading, success, error, empty, disabled, and validation states.
- Do not keep tests that only prove a prop is rendered unless that is the behavior under change.

```tsx
import userEvent from "@testing-library/user-event";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

describe("SaveButton", () => {
  it("does not submit while disabled", async () => {
    const user = userEvent.setup();
    const onSave = vi.fn();

    render(<SaveButton disabled onSave={onSave} />);
    await user.click(screen.getByRole("button", { name: /save/i }));

    expect(onSave).not.toHaveBeenCalled();
  });
});
```

## Coverage and Waste

- Use coverage to find untested behavior, not to force meaningless assertions.
- Raise thresholds only when the suite already tests important paths.
- Remove tests that duplicate broader behavior tests, assert implementation details, or only lock trivial defaults.
- Prefer a missing edge-case test over another happy-path test.
