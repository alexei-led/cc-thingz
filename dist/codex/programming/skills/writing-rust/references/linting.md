# Rust linting

Use before changing Rust format, Clippy, cargo check, CI gates, or slow lint workflows.

## Tooling

Rust's normal toolchain is Cargo plus rustup components:

- `cargo fmt` / `rustfmt` — format Rust code.
- `cargo clippy` — catch common mistakes and idiom issues.
- `cargo check` — fast type and borrow checking without building final artifacts.
- `cargo test` — compile and run unit, integration, and documentation tests.

Install missing optional components with rustup when the user approves:

```bash
rustup component add rustfmt clippy rust-analyzer
```

Do not install tools during a task unless the user asked for setup.

## Fast feedback

Use project commands first. Otherwise prefer package- or manifest-scoped checks:

```bash
cargo fmt --check
cargo check -p crate_name --all-targets
cargo clippy -p crate_name --all-targets -- -D warnings
cargo test -p crate_name test_name
```

For a single edited file, `rustfmt --edition <edition> path.rs` is acceptable in an interactive hook, but final verification should use `cargo fmt --check` so Cargo applies the crate's conventions.

## Clippy

- Treat Clippy output as code feedback, not style trivia.
- Prefer fixing warnings over adding `#[allow(...)]`.
- If an allow is needed, keep it as narrow as possible and state the invariant or false positive.
- Use `cargo clippy --fix --allow-dirty --allow-staged` only on the scoped package or workspace after inspecting what it may change.
- Avoid `--all-features` when the crate documents mutually exclusive features; otherwise use the project's configured CI flags.

## Workspaces and features

- Inspect `[workspace]`, `workspace.default-members`, package features, and CI before picking `--workspace`, `--all-targets`, or `--all-features`.
- In large workspaces, run focused `-p` checks during edits and the configured full gate before final output.
- Keep feature combinations explicit. Do not silently change default features to pass a check.

## Do not weaken signal

- Do not lower lint levels, remove `deny`, or add broad allows just to make a command green.
- Do not hide generated, vendor, target, or fixture issues with ad hoc filters when normal Cargo/rustfmt config should own the exclusion.
- Do not use `cargo clean` as a routine fix for stale errors; it is slow and destroys useful cache state.

## Final gates

Use the project's configured command when present. Otherwise a solid default is:

```bash
cargo fmt --check
cargo clippy --all-targets -- -D warnings
cargo test --all-targets
```

Add `cargo test --doc` when doctests are part of the changed public docs or when nextest is the main runner.
