# Rust Tests

Use writing-rust for toolchain commands.

- Unit tests in `#[cfg(test)] mod tests` for private logic worth covering; `tests/*.rs` for public crate or CLI behavior; doctests for copyable public examples.
- nextest (when the project uses it) does not run doctests; add `cargo test --doc`.
- Filter by package and test name in the edit loop; keep full workspace runs, coverage, Miri, and benchmarks as separate tiers. Never `cargo clean` as a routine step.
- Assert error variants or messages only when callers depend on them.
- Prefer small fakes behind local traits over mock frameworks. Add crates such as `assert_cmd`, `tempfile`, `insta`, `proptest`, `mockall`, or `wiremock` only when already used or justified.
- Async tests use the project's macro (`#[tokio::test]`); no blocking mutex guard across `.await`; channels, barriers, or paused time instead of sleeps.
- Normalize volatile snapshot output (paths, timestamps, ordering).
- For unsafe or concurrency-sensitive code, run configured Miri, loom, or sanitizers and report when unavailable.
