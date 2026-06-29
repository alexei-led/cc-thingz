# Rust testing

Read before adding or reshaping Rust tests.

## Defaults

- Use Cargo's built-in test harness by default.
- Put unit tests next to code under `#[cfg(test)] mod tests` when they exercise local behavior.
- Put integration tests in `tests/*.rs` when they exercise the public crate API, CLI, or real wiring.
- Keep doctests correct for public examples; they run under `cargo test` by default.
- Test behavior through public APIs and stable crate boundaries.

## Commands

Prefer project commands first. If none exist, choose the narrowest useful command:

```bash
cargo test -p crate_name test_name
cargo test --manifest-path path/to/Cargo.toml test_name
cargo test --all-targets
cargo test --doc
cargo nextest run -p crate_name
```

Use nextest only when the project already has it. Run doctests separately with `cargo test --doc` when nextest is the main runner.

## Test design

- Cover success, error, boundary, parsing, serialization, permission, and concurrency cases when relevant.
- Prefer clear test functions over abstract helper layers.
- Use small case tables for input/output matrices when they improve readability.
- Name cases so failures explain the broken behavior.
- Keep fixtures in `tests/fixtures` or `testdata` when files are clearer than inline strings.
- Avoid comments in tests. Add one only for unobvious fixtures, timing, concurrency, unsafe invariants, or regression context.

## Assertions

- Use stdlib assertions by default: `assert!`, `assert_eq!`, `assert_ne!`, `matches!`.
- Compare structured values instead of strings when possible.
- Assert error variants or stable messages only when callers depend on them.
- Do not snapshot volatile values without normalization.

## Mocks and fakes

- Mock only system boundaries: network, filesystem, clock, randomness, subprocesses, external services.
- Prefer small in-memory fakes or test implementations of local traits.
- Avoid broad mock traits that mirror a whole subsystem.
- Add crates such as `mockall`, `assert_cmd`, `tempfile`, `insta`, `proptest`, or `wiremock` only when the project already uses them or the benefit is concrete.

## Async and concurrency tests

- Use the project's runtime test macro, such as `#[tokio::test]`, only when async behavior is required.
- Avoid sleeps. Use channels, barriers, fake clocks, or timeout-bounded awaits.
- Do not share mutable globals across parallel tests.
- Use `loom`, Miri, or sanitizers only when configured or when unsafe/concurrent code warrants the extra gate.

## Fast feedback

- Prefer focused package, manifest, and test-name filters while editing.
- Keep full workspace tests, nextest full runs, coverage, Miri, and benchmarks out of the hot path unless they are the task.
- Do not run `cargo clean` to fix ordinary failures; preserve incremental caches.
- Use `-- --nocapture` only when debugging output.

## Hygiene

- Use temporary directories for filesystem side effects.
- Use helper functions for repeated setup, not for hiding assertions.
- Keep tests deterministic: no real network, current time, random data, or process-global state unless isolated.
- Delete duplicate shallow tests once a stronger public-boundary test covers the behavior.

## Coverage

Coverage is a signal, not the goal. Use `cargo llvm-cov`, `tarpaulin`, or project-specific coverage tools only when configured or requested. Prioritize edge cases and failure paths over line-count padding.
