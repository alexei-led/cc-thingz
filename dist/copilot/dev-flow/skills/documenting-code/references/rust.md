# Rust documentation

Use this only for Rust files. The host skill owns scope, editing, and verification.

## Public API docs

- Use `///` doc comments on every public item: functions, types, traits, constants, modules, and `impl` blocks when the impl adds notable behavior.
- Write doc comments that describe what the item does, the preconditions callers must meet, and the effects (return values, panics, errors, side effects).
- Use `# Panics`, `# Errors`, `# Safety`, and `# Examples` sections where relevant.
  - `# Safety` is required for every `unsafe fn` and `unsafe impl`.
  - `# Panics` is required whenever a function can panic on bad input.
  - `# Errors` is required when a function returns `Result`.
- Write at least one `# Examples` doc-test for public functions in library crates so rustdoc compiles it.
- Use `//!` crate-level and module-level doc comments to describe the purpose, entry points, and usage model.

Good:

````rust
/// Creates a bounded worker pool and returns a handle for submitting tasks.
///
/// # Errors
///
/// Returns [`PoolError::CapacityZero`] when `capacity` is 0.
///
/// # Examples
///
/// ```
/// # use mylib::WorkerPool;
/// let pool = WorkerPool::new(4)?;
/// # Ok::<_, Box<dyn std::error::Error>>(())
/// ```
pub fn new(capacity: usize) -> Result<Self, PoolError> {
````

Avoid:

```rust
/// Creates a worker pool.
pub fn new(capacity: usize) -> Result<Self, PoolError> {
```

## Comments

Keep `//` comments that explain:

- why an `unsafe` block is sound (invariant that makes it safe)
- non-obvious lifetime or borrow choices
- intentional `#[allow(...)]` suppressions with the reason
- performance rationale for a hot-path decision
- accepted trade-offs in concurrency or memory layout

Delete comments that restate type names, match arms, or obvious control flow.

## Tests

Prefer descriptive test function names and small case tables over comments inside `#[test]` functions. Keep a comment only when it explains a non-obvious external invariant or why a tricky edge case matters.

## README and docs

- `cargo build`, `cargo test`, and `cargo run` examples must match the current workspace and edition.
- Keep crate names, feature flags, and dependency version requirements current.
- Architecture docs should cite crate boundaries and public trait contracts, not internal struct layouts.

## Checks

Prefer configured project checks. If available, use narrow docs or Rust checks:

```bash
cargo doc --no-deps
cargo test --doc
cargo clippy -- -D warnings
```

If a tool is missing, inspect public items manually and report the gap.
