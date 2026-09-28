# Rust Linting

Use the project's commands first. Edit loop, scoped to one package:

```bash
cargo check -p crate_name --all-targets
cargo clippy -p crate_name --all-targets -- -D warnings
cargo fmt --check
```

- In a single-file edit hook, `rustfmt --edition <edition> path.rs` is fine; the final check is `cargo fmt --check` so Cargo applies crate settings.
- Fix Clippy warnings instead of adding `#[allow(...)]`. A needed allow stays narrow and states the invariant or false positive.
- Run `cargo clippy --fix --allow-dirty --allow-staged` only on a scoped package, after reviewing what it may change.
- Read `[workspace]`, `default-members`, features, and CI flags before choosing `--workspace`, `--all-targets`, or `--all-features`. Do not change default features to pass a check.
- Do not lower lint levels, remove `deny`, or add broad allows to get green.
- Install missing components (`rustup component add rustfmt clippy`) only when the user asked for setup.
