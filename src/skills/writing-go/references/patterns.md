# Go patterns

Read for package layout, interfaces, error handling, service boundaries, concurrency, and comments.

## Package layout

- Use the existing layout unless it is the problem.
- For new binaries, put entrypoints under `cmd/<name>` and private code under `internal/`.
- Use `pkg/` only for libraries meant for external import.
- Keep domain packages free of HTTP, CLI, database, queue, and vendor SDK types.
- Put adapters near the boundary they serve: HTTP handlers, repositories, clients, workers.

## Interfaces

- Define interfaces at the consumer, not at the implementation.
- Keep interfaces private unless another package must implement or accept them.
- Keep interfaces focused on one behavior; most seams need one or two methods.
- Use an interface for a real seam: multiple implementations, an external boundary, or a useful test fake.
- Do not add one-method interfaces around every concrete type by default.

## Errors

- Add operation context where the error crosses a meaningful boundary.
- Preserve identity with `%w` when callers use `errors.Is` or `errors.As`.
- Expose sentinel errors only for stable branch conditions.
- Prefer typed errors only when callers need structured fields.
- Do not return raw storage, HTTP, or vendor errors from domain APIs.
- Do not turn normal runtime failures into panics.

## HTTP and services

- Handlers decode, validate, call services, and encode responses.
- Services own business rules and return domain errors.
- Repositories and clients hide persistence or vendor details behind concrete adapters.
- Map domain errors to HTTP status, CLI exit code, or worker retry behavior at the edge.
- Keep request-scoped values explicit; avoid hidden globals.

## Configuration

- Load and validate configuration at process startup.
- Keep config parsing outside domain packages.
- Pass typed config into constructors.
- Keep secret values out of logs and errors.

## Concurrency

- Prefer simple synchronous code until concurrency has a measurable need.
- Use existing `errgroup` when goroutines must return errors or share cancellation; add it only when the dependency is justified.
- Use `sync.WaitGroup.Go` when the module target supports it and no error propagation is needed.
- The sender closes channels. Receivers do not close channels they do not own.
- Protect shared mutable state with ownership, channels, or locks. Pick one clear model.
- Avoid sleep-based coordination in tests.

## Naming and comments

- Avoid package stutter: `user.Store`, not `user.UserStore`.
- Use short local names in short scopes; use clear names at package and API boundaries.
- Receiver names are short and consistent.
- Comments explain contracts, invariants, surprising behavior, or tuning decisions.
- Do not comment obvious code.

## Avoid

- `any` as a shortcut around unclear data modeling.
- Global mutable state outside process setup or caches with clear synchronization.
- Thin wrappers that only forward calls and add no boundary, context, validation, or behavior.
- Trivial getters for exported fields.
- Large `manager`, `service`, or `repository` interfaces that mirror a whole subsystem.
