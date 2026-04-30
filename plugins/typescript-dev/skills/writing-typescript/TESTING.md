# TypeScript Testing Reference

## Test Design

- Test behavior through public interfaces, not private helpers.
- Prefer integration-style tests when they give a stable signal.
- Mock only system boundaries: HTTP APIs, time, randomness, filesystem, browser APIs.
- Do not mock internal collaborators just to assert call counts.
- Use red-green-refactor for risky changes: one failing test, minimal code, refactor only when green.
- Delete shallow tests once deeper interface tests cover the behavior.

## Framework: Vitest

```bash
bun add -d vitest @testing-library/react @testing-library/jest-dom
```

## Unit Tests

```typescript
import { describe, it, expect } from "vitest";

describe("validateEmail", () => {
  it("accepts valid email", () => {
    expect(validateEmail("user@example.com")).toBe(true);
  });

  it("rejects empty string", () => {
    expect(validateEmail("")).toBe(false);
  });

  it("rejects invalid format", () => {
    expect(validateEmail("invalid")).toBe(false);
  });
});
```

## Async Tests

```typescript
describe("fetchUser", () => {
  it("returns user data", async () => {
    const user = await fetchUser("123");
    expect(user.id).toBe("123");
  });

  it("throws on not found", async () => {
    await expect(fetchUser("unknown")).rejects.toThrow("Not found");
  });
});
```

## Mocking

**Use Vitest's built-in `vi` utilities for all mocking. Use msw for HTTP APIs.**

### Mock Functions

| Function      | Use When                                                      |
| ------------- | ------------------------------------------------------------- |
| `vi.fn()`     | Standalone mock function for return values and assertions     |
| `vi.spyOn()`  | Spy on existing method while keeping original (use sparingly) |
| `vi.mock()`   | Mock entire module (hoisted, applies module-wide)             |
| `vi.mocked()` | Wrap for type-safe access: `vi.mocked(fn)`                    |

```typescript
import { vi, describe, it, expect, beforeEach, afterEach } from "vitest";

// Always cleanup mocks
afterEach(() => {
  vi.restoreAllMocks();
  vi.resetAllMocks();
});
```

### Argument Matching (CRITICAL)

**Choose matchers deliberately—don't over-match or under-match:**

| Matcher                     | Use When                                                   |
| --------------------------- | ---------------------------------------------------------- |
| Exact value                 | Business-critical values (IDs, keys, table names)          |
| `expect.any(Type)`          | Type check without exact value (generated IDs, timestamps) |
| `expect.objectContaining()` | Partial object matching                                    |
| `expect.stringContaining()` | Partial string matching                                    |

```typescript
describe("UserService", () => {
  it("calls repository with exact business values", async () => {
    const mockRepo = { save: vi.fn() };
    const service = new UserService(mockRepo);

    await service.processOrder("order-123", "customer-456");

    // GOOD: Exact values for business-critical parameters
    expect(mockRepo.save).toHaveBeenCalledWith("order-123", "customer-456");
  });

  it("uses expect.any for generated values", async () => {
    const mockRepo = { save: vi.fn() };
    const service = new UserService(mockRepo);

    await service.createUser({ email: "test@example.com" });

    // GOOD: Exact value for email, any for generated ID
    expect(mockRepo.save).toHaveBeenCalledWith(
      expect.objectContaining({
        email: "test@example.com",
        id: expect.any(String),
        createdAt: expect.any(Date),
      }),
    );
  });

  it("validates SQL query patterns", async () => {
    const mockDb = { exec: vi.fn() };

    await mockDb.exec("INSERT INTO users (id, email) VALUES (?, ?)");

    // GOOD: Pattern match for SQL
    expect(mockDb.exec).toHaveBeenCalledWith(
      expect.stringContaining("INSERT INTO users"),
    );
  });
});
```

### Type-Safe Mocking

```typescript
import { vi, type MockedFunction } from "vitest";
import { fetchUser } from "./api";

// Type-safe mock wrapping
vi.mock("./api");
const mockedFetchUser = vi.mocked(fetchUser);

// Now properly typed
mockedFetchUser.mockResolvedValue({ id: "123", name: "Test" });
```

### Module Mocking

```typescript
import { vi, describe, it, expect } from "vitest";
import { sendEmail } from "./email";
import { createUser } from "./user-service";

// Full module mock
vi.mock("./email", () => ({
  sendEmail: vi.fn(),
}));

// Partial module mock (keep some real implementations)
vi.mock("./utils", async (importOriginal) => {
  const mod = await importOriginal<typeof import("./utils")>();
  return {
    ...mod,
    generateId: vi.fn(() => "test-id"),
  };
});

describe("createUser", () => {
  it("sends welcome email with correct data", async () => {
    await createUser({ email: "test@example.com" });

    expect(sendEmail).toHaveBeenCalledWith(
      expect.objectContaining({ to: "test@example.com" }),
    );
  });
});
```

### HTTP Mocking with msw

**Prefer msw over vi.mock for API testing:**

```typescript
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";

const server = setupServer(
  http.get("/api/users/:id", ({ params }) => {
    return HttpResponse.json({ id: params.id, name: "Test" });
  }),
  http.post("/api/users", async ({ request }) => {
    const body = await request.json();
    return HttpResponse.json({ id: "new-123", ...body }, { status: 201 });
  }),
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

### Common Mistakes to Avoid

- **Forgetting cleanup**: Always use `afterEach(() => { vi.restoreAllMocks() })`
- **Partial mocks with spyOn**: Prefer full `vi.mock` for isolation
- **Missing vi.mocked**: Lose type inference without it
- **Mocking internals**: `vi.mock` only affects external imports
- **Not using msw for HTTP**: vi.mock fetch is brittle—use msw
- **Wrong mock location**: vi.mock must be at top level (hoisted)

## React Component Tests

```typescript
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";

describe("Button", () => {
  it("renders label", () => {
    render(<Button label="Click me" onClick={() => {}} />);
    expect(screen.getByText("Click me")).toBeInTheDocument();
  });

  it("calls onClick when clicked", () => {
    const handleClick = vi.fn();
    render(<Button label="Click" onClick={handleClick} />);

    fireEvent.click(screen.getByRole("button"));

    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it("is disabled when disabled prop is true", () => {
    render(<Button label="Click" onClick={() => {}} disabled />);
    expect(screen.getByRole("button")).toBeDisabled();
  });
});
```

## Hook Tests

```typescript
import { renderHook, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";

describe("useUser", () => {
  it("fetches user data", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ id: "123", name: "Test" }),
    } as Response);

    const { result } = renderHook(() => useUser("123"));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.user).toEqual({ id: "123", name: "Test" });
  });
});
```

## API Route Tests

```typescript
import { describe, it, expect } from "vitest";

describe("POST /api/users", () => {
  it("creates user with valid data", async () => {
    const response = await app.request("/api/users", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: "test@example.com", name: "Test" }),
    });

    expect(response.status).toBe(201);
    const data = await response.json();
    expect(data.id).toBeDefined();
  });

  it("returns 400 for invalid data", async () => {
    const response = await app.request("/api/users", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: "invalid" }),
    });

    expect(response.status).toBe(400);
  });
});
```

## Coverage

```bash
vitest --coverage
vitest --coverage --coverage.thresholds.lines=80
```

## Configuration (vitest.config.ts)

```typescript
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./tests/setup.ts"],
    coverage: {
      reporter: ["text", "html"],
      exclude: ["node_modules/", "tests/"],
    },
  },
});
```

## Guidelines

**CRITICAL: Zero tolerance for test waste**

- **No pointless tests**: Don't test trivial behavior (prop renders, default state)
- **No naive tests**: Don't just test obvious happy paths—include edge cases
- **No duplicate tests**: Same scenario tested multiple ways → keep one, delete others
- **Combine with test.each**: 2+ tests for same function → single `it.each` (mandatory)
- **No comments in tests**: Tests should be self-explanatory unless logic is genuinely non-obvious

**Standard Guidelines**

- Test behavior, not implementation
- Use descriptive test names with template strings: `("validates $input → $expected", ...)`
- One assertion per test (when practical)
- Mock external dependencies with msw for APIs
- Keep tests independent
- Query by role for React components (validates accessibility)
