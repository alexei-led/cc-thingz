# Rust Testing

## Layout

- Unit tests in `#[cfg(test)] mod tests` next to the code; public-API and CLI tests in `tests/*.rs`; fixtures in `tests/fixtures/` or `testdata/`.
- Public doc examples are doctests; keep them compiling.
- Stdlib assertions (`assert!`, `assert_eq!`, `matches!`) by default. Compare structured values, not formatted strings.
- Add `mockall`, `assert_cmd`, `tempfile`, `insta`, `proptest`, or `wiremock` only when the project already uses them or the benefit is concrete. Normalize volatile values before snapshotting.

## Fast Loop

```bash
cargo test -p crate_name test_name
cargo test --manifest-path path/to/Cargo.toml test_name
cargo nextest run -p crate_name        # only when the project uses nextest
cargo test --doc                        # --all-targets and nextest skip doctests
```

- Keep full-workspace runs, coverage (`cargo llvm-cov`, tarpaulin), Miri, and benchmarks off the hot path unless they are the task.
- Use `-- --nocapture` only while debugging output.

## Async and Concurrency

- Use the runtime's test macro (`#[tokio::test]`) only when the code under test is async.
- Replace sleeps with channels, barriers, paused or fake clocks, or timeout-bounded awaits.
- Use `loom`, Miri, or sanitizers when configured, or when `unsafe` or lock-free code warrants them.
