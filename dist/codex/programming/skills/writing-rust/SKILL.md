---
{"description":"Idiomatic Rust development. Use when writing Rust code, Cargo crates/workspaces, Rust tests, or rustfmt/clippy/cargo workflows. Emphasizes ownership, Result errors, small APIs, stdlib-first dependencies, fast cargo feedback, and behavior tests. NOT for Go, Python, TypeScript, shell scripts, or infra-only work.","name":"writing-rust"}
---
<!-- Codex platform guidance -->
<!-- Use this platform's installed tool names exactly for shell, file reads, and search. If a referenced helper or optional tool is unavailable, say so and continue with built-in tools. -->


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
- `unwrap`/`expect` in production code only with a named local invariant.
- When the borrow checker objects, fix the data flow before reaching for `clone()`. Use lifetimes in APIs only for real zero-copy needs.
- Async only where the runtime or I/O boundary requires it. Never hold a blocking mutex guard across `.await`. Bound channels, queues, and retries.
- Keep secrets out of `Debug` output, logs, errors, and snapshots.
- `unsafe`: small blocks behind a safe API, a `// SAFETY:` comment stating the invariant, and focused tests or configured Miri.

## Checks

```bash
cargo fmt --check
cargo clippy --all-targets -- -D warnings
cargo test --all-targets
cargo test --doc    # --all-targets and nextest both skip doctests
```

Never run `cargo clean` as a routine fix; it throws away the incremental cache.

## References

- [testing.md](references/testing.md): read when adding or reshaping tests, or when the test loop is slow.
- [linting.md](references/linting.md): read when changing rustfmt, Clippy, or workspace/feature check flags.

Done when the relevant build/test/lint checks pass on what you changed, or you name each check that did not run and why.
