# Rust fix reference

Use for Rust defect fixes. The host skill owns the full fix workflow; this file adds language-specific repro commands and key failure patterns.

## Repro and narrow loop

Find the fastest reliable failing signal first:

```bash
cargo test -p crate_name test_name -- --nocapture
cargo test --manifest-path path/to/Cargo.toml test_name
cargo clippy --all-targets -- -D warnings
cargo check --all-targets
```

Use the narrowest `-p` and test name filter while editing. Run `cargo test --all-targets` or the project gate before final output. Preserve the incremental build cache; do not use `cargo clean` as a routine fix step.

## Key failure patterns

- `unwrap()` or `expect()` on `None` or `Err` in a path that can actually fail; use proper error propagation.
- Borrow or lifetime error that indicates a design issue (shared mutable state); fix ownership, not the diagnostic.
- Integer overflow in release mode (`u32::MAX + 1` wraps silently); use checked or saturating arithmetic for user-controlled inputs.
- Blocking call (`std::fs`, `std::net`, `std::thread::sleep`) inside an async function on a non-blocking executor; use async equivalents.
- `Arc<Mutex<T>>` deadlock from nested lock acquisition or lock held across `.await`.
- Undefined behavior in `unsafe` block: wrong pointer alignment, invalid transmute, or aliased mutable reference.

## Verification

Before claiming fixed:

- Failing test or repro no longer fails.
- `cargo clippy --all-targets -- -D warnings` exits clean.
- `cargo check --all-targets` exits clean.
- For concurrency changes: run with the race sanitizer or Miri when configured (`RUSTFLAGS="-Zsanitizer=thread" cargo test` requires nightly).
- For unsafe changes: run Miri (`cargo miri test`) when available and document the invariant in a comment.
