# TypeScript Documentation

Use this only for TypeScript or JavaScript files. The host skill owns scope,
editing, and verification.

## Public API docs

- Public exported APIs need TSDoc/JSDoc when behavior, constraints, errors, or side effects are not obvious from names and types.
- Do not repeat type annotations in prose.
- Use `@param`, `@returns`, `@throws`, `@deprecated`, and `@example` only when they add useful information.
- Document complex generics, discriminated unions, utility types, and public contracts when the type alone is hard to understand.

Good:

```typescript
/**
 * Creates a client and validates required auth configuration.
 *
 * @throws ConfigError when baseUrl or token is missing.
 */
export function createClient(config: ClientConfig): Client;
```

Avoid comments that only restate the function name or parameter types.

## Comments

Keep comments that explain:

- business rules or invariants
- browser/runtime constraints
- external API limits
- why a workaround or unsafe cast is necessary

Delete comments that paraphrase code.

## Tests

Prefer descriptive test names and clear assertions. Avoid comments unless they
explain non-obvious external behavior, fixtures, timing, or edge-case rationale.

## README and examples

- `npm`, `pnpm`, `yarn`, or `bun` commands must match the repo's package manager.
- Examples should compile with current types when practical.
- Document unusual `tsconfig` or runtime constraints only when users need them.

## Checks

Prefer configured project checks. If available, use narrow docs/type checks:

```bash
bunx tsc --noEmit
bunx typedoc --out docs src/
```

If TypeDoc is not configured, skip it and inspect exported APIs manually.
