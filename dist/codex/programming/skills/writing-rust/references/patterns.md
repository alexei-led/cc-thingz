# Rust patterns

Read for crate layout, modules, ownership, traits, errors, async, unsafe, and public APIs.

## Cargo and crate layout

- Use the existing layout unless it is the problem.
- Put reusable APIs in `src/lib.rs`; put process entrypoints in `src/main.rs` or `src/bin/*.rs`.
- Use `tests/` for integration tests, `examples/` for runnable examples, and `benches/` only when the project already has benchmark tooling.
- In workspaces, keep shared dependencies, lints, and package metadata in the workspace root when the project already centralizes them.
- Keep domain crates free of HTTP, CLI, database, queue, and vendor SDK types.

## Modules and visibility

- Prefer small modules with clear ownership. Split by responsibility, not by type category alone.
- Keep visibility narrow: private first, then `pub(crate)`, then public API only when needed externally.
- Avoid broad preludes unless the project already uses them and they stay stable.
- Re-export deliberately from crate boundaries; do not leak internal module structure by accident.

## Ownership

- Accept borrowed inputs for read-only work: `&str`, `&Path`, `&[T]`.
- Own data in structs, spawned tasks, caches, and cross-thread boundaries.
- Prefer `Cow` only when profiling or API shape shows mixed borrowed/owned data is worth the complexity.
- Avoid lifetime-heavy APIs unless zero-copy behavior is a real requirement.
- Avoid cloning large values in loops or hot paths; change ownership flow or borrow instead.

## Types and traits

- Use newtypes for domain IDs, tokens, units, and values with validation rules.
- Use enums for variants and state machines. Avoid parallel booleans or string state.
- Implement standard traits before custom methods when they express the contract.
- Use builders only for many optional fields, validated construction, or readable test setup.
- Keep trait objects, generics, and macros local unless they buy clear reuse or boundary isolation.

## Errors

- Add operation context where errors cross a boundary.
- Preserve error identity when callers need `match`, `source`, or conversion behavior.
- Do not expose raw storage, HTTP, parser, or vendor errors from domain APIs.
- Keep CLI and HTTP error-to-exit/status mapping at the boundary.
- Use `thiserror` for library error enums only when the crate already uses it or boilerplate justifies it.
- Use `anyhow` for binary/application glue only when typed branching is not required.

## Async and concurrency

- Keep sync code sync until async is required by I/O or the surrounding framework.
- Pass shared state explicitly, usually as `Arc<T>` with a clear lock or channel ownership model.
- Prefer message passing or ownership transfer over shared mutable state when it makes ordering clearer.
- Do not hold a blocking mutex guard across `.await`.
- Bound channels, tasks, retries, and queues unless unbounded behavior is deliberate and documented.

## Serialization and boundaries

- Validate untrusted JSON, TOML, CLI args, environment, and filesystem input at the boundary.
- Keep serde DTOs at I/O boundaries when domain invariants need stronger types.
- Use `Path`/`PathBuf` for filesystem paths, not strings.
- Keep secrets out of `Debug`, logs, errors, and snapshots.

## Unsafe and FFI

- Prefer safe wrappers around FFI, raw pointers, and global state.
- Document ownership, aliasing, lifetime, thread-safety, and panic-safety assumptions.
- Keep unsafe code out of generic business logic.

## Avoid

- `unwrap`/`expect` in production flow without a named local invariant.
- `clone()` as a first response to borrow checker errors.
- Public fields that bypass validation.
- One-off trait abstractions or macros that hide simple control flow.
- `String` paths, stringly typed states, and magic feature names.
- Disabling lints instead of fixing code, unless the allow is narrow and justified.
