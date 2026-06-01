# Go principles

Read before writing, changing, or reviewing Go code.

## Scope

- Use these rules for Go source, tests, APIs, and CLI code.
- Do not apply them to Python, TypeScript, shell-only, or infrastructure-only tasks.
- Project conventions win when they are safe and consistent.

## Defaults

- Start from `go.mod`, the module Go version, existing dependencies, CI, and nearby code.
- Prefer stdlib and existing dependencies. Add a package only for a concrete requirement.
- Keep packages cohesive: domain logic separate from transport, persistence, config, and process I/O.
- Keep exported API small. Export only stable names used outside the package.

## Types and interfaces

- Prefer concrete types for domain data and business logic.
- Use generics for reusable algorithms, not to avoid modeling a domain type.
- Avoid `any` and `interface{}` unless the value is genuinely unconstrained.
- Producers return concrete types. Consumers define the smallest private interface they need.
- Wrap external clients in concrete adapters so vendor types do not leak through the domain.

## Context and errors

- Pass `context.Context` as the first parameter for work that can block, cancel, or cross a boundary.
- Do not store `context.Context` in structs.
- Return `error` for expected failures. Use `panic` only for programmer errors or impossible initialization states.
- Wrap lower-level errors with `%w` when the added operation context helps diagnosis.
- Use sentinel or typed errors only when callers need distinct behavior.
- Keep HTTP, CLI, and worker error mapping at the boundary.

## Flow and concurrency

- Use guard clauses and early returns. Avoid deep nesting.
- Start goroutines only with a clear owner, cancellation path, and completion path.
- Prefer deterministic tests over sleeps for timers, goroutines, and channel behavior.

## Tests and verification

- Test externally visible behavior, not private helper trivia.
- Cover success, failure, boundary, cancellation, and concurrency behavior when relevant.
- Mock only system boundaries. Prefer small fakes when they keep tests clearer than generated mocks.
- Run the project-configured verification gates before claiming success.
- If a gate fails, diagnose from the actual output before changing code again.

## Safety

- Do not run destructive commands without explicit approval.
- For broad rewrites, data loss risk, generated-file churn, or dependency changes, state the risk first and ask.
