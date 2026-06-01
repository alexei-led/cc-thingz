# TypeScript Patterns

Use for data models, validation, async flow, and module boundaries.

## Strict Data Models

- Prefer named domain types and constants over repeated raw strings.
- Use branded primitives only when ID mixups are likely.
- Use interfaces for extensible object contracts and public APIs when project style allows it.
- Use type aliases for unions, mapped types, utility types, and closed variants.
- Use `satisfies` for config maps so values stay narrow while keys are checked.

```typescript
const ROLES = ["admin", "user", "guest"] as const;
type Role = (typeof ROLES)[number];
type UserId = string;

interface User {
  id: UserId;
  email: string;
  role: Role;
}

const routes = {
  home: { path: "/" },
  user: { path: "/users/:id", requiresAuth: true },
} satisfies Record<string, { path: string; requiresAuth?: boolean }>;
```

## Variants and State

Use discriminated unions instead of boolean-flag objects.

```typescript
type LoadState<T> =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "success"; data: T }
  | { status: "error"; error: string };

function renderLabel<T>(state: LoadState<T>): string {
  switch (state.status) {
    case "idle":
      return "Idle";
    case "loading":
      return "Loading";
    case "success":
      return "Loaded";
    case "error":
      return state.error;
    default: {
      const exhaustive: never = state;
      return exhaustive;
    }
  }
}
```

## Boundary Validation

Narrow `unknown` before returning typed data. Check value types, not only key presence.

```typescript
function isRecord(value: unknown): value is Record<PropertyKey, unknown> {
  return typeof value === "object" && value !== null;
}

function isUser(value: unknown): value is User {
  if (!isRecord(value)) return false;
  return (
    typeof value.id === "string" &&
    typeof value.email === "string" &&
    (value.role === "admin" || value.role === "user" || value.role === "guest")
  );
}
```

Use the existing schema library when the project has one. Add one only for real validation complexity.

```typescript
const UserSchema = z.object({
  id: z.string(),
  email: z.string().email(),
  role: z.enum(["admin", "user", "guest"]),
});

type User = z.infer<typeof UserSchema>;

function parseUser(value: unknown): User {
  return UserSchema.parse(value);
}
```

## Result and Async Flow

Use explicit results for recoverable failures. Validate response bodies before returning domain data.

```typescript
type Ok<T> = { ok: true; value: T };
type Err<E> = { ok: false; error: E };
type Result<T, E> = Ok<T> | Err<E>;

const ok = <T>(value: T): Ok<T> => ({ ok: true, value });
const err = <E>(error: E): Err<E> => ({ ok: false, error });

async function fetchUser(
  id: string,
  options: { signal?: AbortSignal } = {},
): Promise<Result<User, "not-found" | "invalid-response" | "network">> {
  let response: Response;
  try {
    response = await fetch(`/users/${encodeURIComponent(id)}`, {
      signal: options.signal,
    });
  } catch {
    return err("network");
  }

  if (response.status === 404) return err("not-found");
  if (!response.ok) return err("network");

  let body: unknown;
  try {
    body = await response.json();
  } catch {
    return err("invalid-response");
  }

  if (!isUser(body)) return err("invalid-response");
  return ok(body);
}
```

## Control Flow

- Prefer guard clauses over nested conditionals.
- Keep validation, I/O, domain decisions, and formatting in separate functions.
- Use small predicate helpers when they improve narrowing or remove duplicated checks.

```typescript
function createReceipt(order: Order | null): Result<Receipt, string> {
  if (!order) return err("order required");
  if (order.items.length === 0) return err("order must have items");
  if (order.total <= 0) return err("invalid total");

  return ok(buildReceipt(order));
}
```

## Module Boundaries

- Pass dependencies as parameters or constructor inputs.
- Keep external SDKs, HTTP clients, storage, and clocks behind narrow interfaces.
- Do not leak transport DTOs into domain logic.
- Keep framework code at the edge: route handlers, controllers, components, or adapters.

```typescript
interface UserRepo {
  findById(id: UserId): Promise<User | null>;
}

function createUserService(userRepo: UserRepo) {
  return {
    async getUser(id: UserId): Promise<Result<User, "not-found">> {
      const user = await userRepo.findById(id);
      if (!user) return err("not-found");
      return ok(user);
    },
  };
}
```

## Anti-Patterns

Flag these unless existing constraints force them:

- `any` where `unknown` plus narrowing works.
- `value as Target`, double assertions, and non-null assertions without a proven invariant.
- Boolean combinations for mutually exclusive states.
- Mixed `null` and `undefined` for the same missing-value meaning.
- Repeated semantic literals for statuses, roles, event names, routes, and error codes.
- God interfaces, deep inheritance, and deep intersection chains.
- Returning parsed JSON, env vars, or SDK data as trusted domain types without validation.
