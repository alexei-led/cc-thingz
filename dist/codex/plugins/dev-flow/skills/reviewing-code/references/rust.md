# Rust Review Reference

Host skill owns scope, severity, scoring, and output. This file adds Rust-specific evidence gathering and checks.

## Tool-enabled review

Run configured project tools only when the active role can execute commands. Prefer project commands when present.

Useful Rust gates:

```bash
cargo build --all-targets
cargo clippy --all-targets -- -D warnings
cargo test --all-targets
cargo test --doc
```

Treat tool output as evidence, then map it through the severity rubric. If a tool is missing or too slow, report the gap and continue source review. Do not install tools.

## Read-only review

When commands are unavailable, use supplied diff, file reads, and caller-supplied output. Follow direct callers for changed public API items, trait implementations, type boundaries, error types, and resource ownership.

## Focus checks

Correctness:

- Unsafe blocks without a documented invariant explaining why the operation is sound.
- Lifetime annotations that hide real borrow or aliasing constraints.
- Integer overflow or truncation in sizes, indices, offsets, or numeric conversions.
- Ignored `Result` or `Option`; silenced with `unwrap`, `expect`, or `?` in contexts where error escalation is wrong.
- Trait object or generic bound mismatch between implementation and caller.

Security:

- Unsafe FFI use that assumes C ownership or alignment conventions without documented proof.
- Command injection via `std::process::Command` built from untrusted input.
- Path traversal from untrusted strings passed to filesystem APIs.
- Weak randomness from `rand` default sources for secrets or tokens; use a CSPRNG explicitly.
- Secret exposure in `Debug` impls, logs, or error messages.
- Missing authorization checks at HTTP handler, RPC, or service boundary seams.

Reliability:

- Missing cancellation or timeout propagation for async tasks, streams, and external calls.
- Blocking operations inside async contexts that starve the executor.
- Resource handles (`File`, connections, guards) not closed or dropped deterministically.
- Retry loops without cap, backoff, or idempotency check.
- Shared mutable state accessed across threads without adequate synchronization.

Performance:

- Cloning heap values in hot paths when a reference or `Cow` suffices.
- Repeated format string allocation where a pre-allocated buffer or `write!` works.
- Unbounded channel or queue growth.
- Avoidable allocations in hot paths only when the path is plausible.

Tests:

- Changed public behavior without `#[test]` or integration test coverage for success, failure, and edge cases.
- Bug fixes without a regression test at the public seam.
- Tests that reach private helpers directly instead of the public crate API.
- Concurrency or unsafe changes without Miri or loom evidence when those tools are configured.

## Version-gated checks

Inspect `Cargo.toml` edition, `rust-toolchain.toml`, and CI before applying version-specific claims.

- `edition = "2024"` changes `unsafe` fn usage rules; do not flag edition-2021 patterns as wrong in edition-2024 code and vice versa.
- Feature flags and cfg conditionals can hide significant code paths; check the relevant enabled features before concluding a path is dead.
- MSRV constraints apply to API usage; flag new stable APIs only when the MSRV allows them.

## Failure handling

- Compile, clippy, or test failure in reviewed scope: Critical when confirmed by tool output.
- Unsafe block without documented invariant: Critical regardless of tool availability.
- Linter warning: severity depends on impact; do not auto-promote to Critical.
- Security context missing across crate boundaries: use Needs review and name the missing trust boundary.
- LSP or graph unavailable: note reduced cross-crate coverage only when it affects the finding.
