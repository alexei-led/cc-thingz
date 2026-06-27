# Rust Test Slice

Use this only for Rust test work. The host skill owns scope, workflow, and output.

## Commands

Use project commands first. If none exist, choose the narrowest useful command:

```bash
cargo test -p crate_name test_name
cargo test --manifest-path path/to/Cargo.toml test_name
cargo test --all-targets
cargo test --doc
cargo nextest run -p crate_name
cargo llvm-cov --workspace
```

Run nextest, coverage, Miri, sanitizers, and benchmarks only when configured or relevant. Nextest does not run doctests; use `cargo test --doc` for documentation examples.

## Learn project patterns

Before changing tests:

- Read 2-3 nearby `*_test` modules or integration tests under `tests/`.
- Check shared helpers, fixtures, `tests/fixtures`, `testdata`, snapshot config, and async runtime setup.
- Follow existing assertion, fixture, and fake conventions unless they are the problem.

## Behavior seams

Prefer public crate APIs, CLI commands, service boundaries, parsers, serializers,
or adapters. Use narrower unit seams only when behavior is pure, local,
deterministic, and cheap.

## Fast feedback defaults

- Prefer package, manifest, and test-name filters while editing.
- Keep full workspace runs, coverage, Miri, and benchmarks out of the every-turn loop unless they are the target signal.
- Preserve Cargo incremental caches. Do not use `cargo clean` as a routine fix.
- Use nextest when the project already uses it for faster full-package feedback.

## Test shape

- Use `#[cfg(test)] mod tests` for unit tests near private implementation details that deserve coverage.
- Use `tests/*.rs` integration tests for public crate behavior or CLI/API seams.
- Use doctests for public examples that users should be able to copy.
- Prefer small case tables for input/output matrices when they improve readability.
- Name test functions and cases after behavior, not implementation steps.

## Assertions and fakes

- Use `assert!`, `assert_eq!`, `assert_ne!`, and `matches!` by default.
- Assert error variants or stable messages only when callers depend on them.
- Mock only system boundaries: network, filesystem, clock, randomness, subprocesses, external services.
- Prefer small fakes implementing local traits over broad mock frameworks.
- Add crates such as `assert_cmd`, `tempfile`, `insta`, `proptest`, `mockall`, or `wiremock` only when already used or explicitly justified.

## Async, concurrency, and unsafe

- Use the project's async test macro, such as `#[tokio::test]`, only for async behavior.
- Avoid sleeps. Use channels, barriers, fake clocks, or timeout-bounded awaits.
- Do not hold blocking mutex guards across `.await` in tests.
- For unsafe or concurrency-sensitive code, run configured Miri, `loom`, or sanitizer checks and report gaps when unavailable.

## Review focus

Flag:

- happy-path-only tests for meaningful logic
- private-helper tests that miss public behavior
- duplicate scenarios that can become clearer case tables
- broad mocks accepting any business value
- missing error, edge, permission, parsing, serialization, concurrency, or regression cases
- doctest drift for public examples
- sleeps, real external services, repeated setup, cache-busting commands, or `cargo clean` in the fast path
- snapshot tests with volatile output and no normalization

## Failure handling

- Compile, test, Miri, or sanitizer failures are blocking when in scope.
- Test failures and coverage gaps belong in findings.
- If tools fail to run, quote output and mark affected checks skipped.
- If no tests exist, report that before other findings.
