# TypeScript Patterns

Use for data models, validation, async flow, and module boundaries. Apply project conventions first.

## Data Models

- Prefer named domain types and constants for repeated semantic values.
- Use branded primitives only when ID mixups are likely; do not alias `string` for false safety.
- Use interfaces for extensible object contracts and public APIs when project style allows it.
- Use type aliases for unions, mapped types, utility types, and closed variants.
- Use `satisfies` for config maps so values stay narrow while keys are checked.

```typescript
const ROLES = ["admin", "user", "guest"] as const;
type Role = (typeof ROLES)[number];

const routes = {
  home: { path: "/" },
  user: { path: "/users/:id", requiresAuth: true },
} satisfies Record<string, { path: string; requiresAuth?: boolean }>;
```

## Variants and State

- Model mutually exclusive states as discriminated unions.
- Use exhaustive switches with a `never` check for closed unions.
- Avoid boolean-flag objects for exclusive states.

## Boundary Validation

- Narrow `unknown` before returning typed domain data.
- Check value types, not only key presence.
- Keep validation close to I/O; return typed domain data from the boundary.
- Use the existing schema library when present. Add one only for real validation complexity.

```typescript
interface User {
  id: string;
  email: string;
  role: Role;
}

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

## Async Flow and Results

- Use explicit results when callers must handle recoverable failures.
- Map transport, parse, validation, and domain failures to distinct variants when callers need different behavior.
- Preserve cancellation and timeout hooks; pass `AbortSignal` through APIs that can outlive the caller.
- Do not cast `await response.json()` directly to a domain type.

## Module Boundaries

- Pass dependencies as parameters; use constructors only in class-based code.
- Keep external SDKs, HTTP clients, storage, and clocks behind narrow interfaces.
- Do not leak transport DTOs into domain logic.
- Keep framework code at the edge: route handlers, controllers, components, or adapters.

## Anti-Patterns

Flag these unless existing constraints force them:

- Mixed `null` and `undefined` for the same missing-value meaning.
- God interfaces, deep inheritance, and deep intersection chains.
- Returning parsed JSON, env vars, or SDK data as trusted domain types without validation.
