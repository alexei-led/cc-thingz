# C# /.NET patterns

Read for solution layout, ASP.NET Core boundaries, DI, EF access, configuration,
workers, and comments.

## Solution and project layout

- Use the existing solution and project structure unless it is the problem.
- Keep app startup thin: compose services, middleware, configuration, and logging at the edge.
- Keep domain code free of controller, transport, ORM, and hosting concerns when there is a stable seam.
- Prefer one clear owner per project: web app, worker, library, tests, or tooling.

## ASP.NET Core boundaries

- Controllers and minimal API handlers parse input, validate, call application services, and map results.
- Keep auth, serialization, caching, and HTTP status mapping at the web boundary.
- Bind request DTOs separately from domain models when the shapes differ.
- Return typed results or the project's established response pattern; do not mix transport concerns into domain services.

## Dependency injection and construction

- Use the built-in DI container unless the project already chose another one.
- Inject concrete collaborators or small consumer-owned interfaces.
- Do not create one-interface-per-class abstractions without a real seam.
- Keep service lifetimes deliberate. Avoid singletons that capture scoped services or mutable request state.

## Data access and EF

- Use the existing data access stack. Do not introduce EF, Dapper, or raw SQL only for preference.
- Keep query composition near repositories or adapters, not spread through handlers.
- Project only the fields needed on read paths.
- Keep transaction, retry, and concurrency-token handling at the persistence boundary.

## Configuration and workers

- Load and validate options at startup.
- Pass typed options or settings into services; avoid scattered config lookups.
- In background services, keep the loop explicit, honor cancellation, and isolate retry/backoff policy.

## Naming and comments

- Use domain names over framework names where possible.
- Comments explain contracts, invariants, or surprising behavior, not what the syntax already says.
- Keep comments short; move longer rationale to docs, issue links, or design notes.
- Delete dead wrappers and pass-through services inside the touched scope.
