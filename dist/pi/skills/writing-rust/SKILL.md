---
{"description":"Idiomatic Rust development. Use when writing Rust code, Cargo crates/workspaces, Rust tests, or rustfmt/clippy/cargo workflows. Emphasizes ownership, Result errors, small APIs, stdlib-first dependencies, fast cargo feedback, and behavior tests. NOT for Go, Python, TypeScript, shell scripts, or infra-only work.","name":"writing-rust"}
---
<!-- Pi platform guidance -->
<!-- Use installed tool names. Discover callable tools before batching independent calls in codemode; model-only UI/orchestration tools must be called directly. -->
<!-- Prefer direct read for required skill/instruction files when exposed; otherwise use Code Mode only after verifying output protection, not assumed nested-path protection. Code Mode composes calls, not durable workflows or context-mode data processing. Async subagents notify natively: yield rather than poll. -->


# Rust Development

Covers crates, workspaces, and Rust CLIs. Check `Cargo.toml`, `rust-toolchain.toml`, and CI before using newer syntax or APIs. Project conventions win over these defaults.

## Version and Features

- Stay within `package.rust-version` (MSRV) and the pinned toolchain unless the task is an upgrade.
- Use Edition 2024 syntax only when the crate sets `edition = "2024"`.
- Keep features additive. Do not assume `--all-features` compiles when the crate documents mutually exclusive features.

## Defaults

- Stdlib and existing crates first. `thiserror` for library error enums and `anyhow` for application glue only when the crate already uses them or boilerplate justifies it.
- Newtypes for IDs, tokens, and validated values; enums for states. Private first, then `pub(crate)`, then `pub`.
- Implement `From`, `TryFrom`, `AsRef`, `FromStr`, and `Display` before ad hoc conversion methods.
- Parsing and validation return `Result` with a typed error. `unwrap`/`expect` in production code only with a named local invariant.
- When the borrow checker objects, fix the data flow before reaching for `clone()`. Use lifetimes in APIs only for real zero-copy needs.
- Async only where the runtime or I/O boundary requires it. Never hold a blocking mutex guard across `.await`. Bound channels, queues, and retries.
- Keep secrets out of `Debug` output, logs, errors, and snapshots.
- `unsafe`: small blocks behind a safe API, a `// SAFETY:` comment stating the invariant, and focused tests or configured Miri.

## Checks

Use the project's configured Cargo commands first. While editing, run focused checks (`cargo check -p <crate>`, `cargo test -p <crate> <name>`); before finishing, run the full gates:

```bash
cargo fmt --check
cargo clippy --all-targets -- -D warnings
cargo test --all-targets   # or cargo nextest run, when the project uses nextest
cargo test --doc           # --all-targets and nextest both skip doctests
```

Test behavior through the public API with valid, invalid, and boundary cases, not private helpers. Never run `cargo clean` as a routine fix; it throws away the incremental cache.

## References

- [testing.md](references/testing.md): read when adding or reshaping tests, or when the test loop is slow.
- [linting.md](references/linting.md): read when changing rustfmt, Clippy, or workspace/feature check flags.

Done when the relevant build/test/lint checks pass on what you changed, or you name each check that did not run and why.
