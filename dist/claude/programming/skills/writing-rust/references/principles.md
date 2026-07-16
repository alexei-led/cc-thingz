# Rust principles

Read before writing, changing, or reviewing Rust code.

## Scope

- Use these rules for Rust source, tests, crates, workspaces, and Cargo tooling.
- Do not apply them to Go, Python, TypeScript, shell-only, or infrastructure-only tasks.
- Project conventions win when they are safe and consistent.

## Defaults

- Start from `Cargo.toml`, `Cargo.lock`, `rust-toolchain.toml`, CI, and nearby code.
- Prefer stdlib and existing crates. Add a crate only for a concrete requirement.
- Keep crates cohesive: domain logic separate from transport, persistence, config, and process I/O.
- Keep public APIs small. Export only stable names needed outside the crate.
- Model domain states with types, enums, and newtypes instead of strings, booleans, or loosely paired values.

## Ownership and types

- Prefer simple ownership over clever lifetimes. Use references for inputs and owned values for stored data.
- Do not clone only to satisfy the borrow checker. First check whether data flow, ownership, or API shape is wrong.
- Use `&str` and `&[T]` for read-only inputs; store `String` and `Vec<T>` when ownership is needed.
- Use `Option` and `Result` instead of sentinel values.
- Derive common traits when useful: `Debug`, `Clone`, `Copy`, `Eq`, `PartialEq`, `Ord`, `Hash`, `Default`.

## Traits and APIs

- Use traits for real seams: multiple implementations, external boundaries, or useful test fakes.
- Keep traits small and local to the consumer when possible.
- Prefer `From`, `TryFrom`, `AsRef`, `Borrow`, `Iterator`, and `IntoIterator` over ad hoc conversion methods.
- Avoid generic type parameters when a concrete type is clearer.
- Keep feature flags additive and documented. Avoid feature combinations that change public semantics silently.

## Errors

- Return `Result` for recoverable failures. Use `panic!` only for programmer errors, impossible invariants, or tests.
- Add context at meaningful boundaries; do not erase typed errors that callers need to branch on.
- Libraries expose stable typed errors when callers need categories. Applications may use `anyhow` only when the project already uses it or approval is given.
- Do not `unwrap` or `expect` in production paths unless the invariant is local, obvious, and the message names the invariant.

## Async, concurrency, and resources

- Use async only when the project already has an async runtime or the boundary requires it.
- Do not block inside async tasks; use the runtime's blocking escape hatch when unavoidable.
- Make cancellation, timeouts, and shutdown explicit at network, process, and long-running boundaries.
- Avoid global mutable state. If shared state is needed, make ownership and locking visible.
- Close or flush resources deliberately. Prefer RAII and scoped lifetimes over manual cleanup flags.

## Unsafe

- Avoid `unsafe` unless a safe API cannot meet the requirement.
- Keep unsafe blocks small and wrapped by a safe API.
- Document the safety invariant next to the unsafe block.
- Add tests for the invariant and run configured Miri or sanitizer checks when available.

## Tests and verification

- Test externally visible behavior, not private helper trivia.
- Cover success, failure, boundary, parsing, serialization, and concurrency behavior when relevant.
- Mock only system boundaries. Prefer small fakes or real in-memory collaborators when cheap.
- Run the project-configured verification gates before claiming success.
- If a gate fails, diagnose from the actual output before changing code again.

## Safety

- Do not run destructive commands without explicit approval.
- Avoid `cargo clean` as a routine fix; it destroys the incremental build cache.
- For broad rewrites, generated-file churn, MSRV changes, feature-flag changes, or dependency changes, state the risk first and ask.
