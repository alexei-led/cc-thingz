---
agent: engineer
allowed-tools:
- Read
- Bash
- Grep
- Glob
- Edit
- Write
- LS
context: fork
description: Idiomatic Rust development. Use when writing Rust code, Cargo crates/workspaces,
  Rust tests, or rustfmt/clippy/cargo workflows. Emphasizes ownership, Result errors,
  small APIs, stdlib-first dependencies, fast cargo feedback, and behavior tests.
  NOT for Go, Python, TypeScript, shell scripts, or infra-only work.
name: writing-rust
user-invocable: false
---

# Rust Development

Use only for Rust crates and Cargo workspaces. Follow the crate's edition, MSRV,
toolchain file, CI, and local style. Rust CLI development (clap, argument
parsing, subcommands) is in scope; apply `patterns.md` and `testing.md` — there
is no dedicated CLI reference.

## Read First

Read [principles.md](references/principles.md) before writing, changing, or reviewing Rust code. Read conditional references only when the change touches that area.

## Conditional References

- [patterns.md](references/patterns.md) — crate layout, modules, ownership, traits, errors, async, unsafe, and public APIs.
- [testing.md](references/testing.md) — adding or reshaping Rust tests; keep the local test loop fast.
- [linting.md](references/linting.md) — changing rustfmt, Clippy, cargo check, CI gates, or slow lint workflows.

## Comments and Rustdoc

- Use `///` or `//!` rustdoc for public APIs when users need contracts, edge cases, examples, or safety notes.
- Add implementation comments only for non-obvious constraints, invariants, side effects, tradeoffs, or unsafe assumptions.
- Keep comments short. Move longer rationale to docs, issue links, or design notes.
- Do not comment obvious code or restate names and types.
- Keep tests readable without comments; add one only for unobvious fixtures, timing, concurrency, unsafe invariants, or regression context.
- Document safety invariants next to `unsafe` blocks.

## Edition and MSRV

- Inspect `Cargo.toml`, `Cargo.lock`, `rust-toolchain.toml`, CI, and nearby code before using edition- or version-specific APIs.
- Do not use APIs newer than `package.rust-version` or the pinned toolchain unless the task is an upgrade.
- Use Edition 2024 syntax only when the crate already opts into `edition = "2024"`.
- Respect feature flags. Do not enable `--all-features` assumptions in code unless incompatible feature combinations are ruled out.

## Verification

Run focused Cargo checks while editing, then the project-configured build, tests,
format, and lint before final output. Prefer:

```bash
cargo fmt --check
cargo clippy --all-targets -- -D warnings
cargo test --all-targets
```

Use `cargo nextest run` when the project already uses nextest. Run `cargo test --doc` separately when doctests matter because nextest does not run doctests.

If a check is unavailable, state that and run the closest configured gate. If a check fails, quote the failure, diagnose the cause, fix one issue, and rerun the relevant check.

## Failure Cases

- No clear Rust root: locate `Cargo.toml` before choosing files, package names, or commands.
- Unknown MSRV or edition: inspect manifests, toolchain files, CI, and lockfiles before using newer syntax or APIs.
- New crate requested: confirm stdlib or existing crates cannot meet the requirement.
- `unsafe` needed: isolate it, document the safety invariant, and add focused tests or run configured Miri checks.
- Broad or risky edit: state the risk and ask before acting. Do not run destructive commands.

## Final Response

Include:

- changed files
- checks run and results
- checks skipped with reasons
- remaining risks or follow-ups
