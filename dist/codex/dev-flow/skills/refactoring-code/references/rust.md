# Rust refactoring reference

Use for Rust behavior-preserving refactors. The host skill owns the scope-mapping workflow and output contract; this file adds language-specific mapping tools, safety gates, and caveats.

## Scope mapping

Before editing:

- Use `rust-analyzer rename` (via LSP in the editor or `rust-analyzer` CLI) for symbol renames — it updates all crate-local usages.
- For renames visible across crate boundaries, also search dependent crates with `rg 'old_name'` since LSP rename stops at the current workspace by default.
- For module or file moves, update `mod` declarations, `use` paths, and any `include!` or `path = "..."` overrides in `Cargo.toml`.
- For trait renames or method renames, check all `impl Trait for T` blocks and `where T: Trait` bounds across the workspace.

## Verification gate

```bash
cargo check --all-targets
cargo clippy --all-targets -- -D warnings
cargo test --all-targets
```

Run `cargo check` before each batch to catch compile errors quickly. Run the full test suite before final output. Use `cargo build` only when linking is needed to verify the final artifact.

## Key caveats

- Renaming a public item in a published crate is a semver-breaking change; add a deprecated re-export alias and bump the minor or major version.
- Moving a module changes its canonical path; all `use crate::old::path::Item` and `pub use` re-exports must be updated.
- Renaming a struct field or enum variant changes derive-generated `Debug`, `serde::Serialize/Deserialize`, and `PartialEq`/`Hash` behavior; check serde `rename`/`rename_all` attributes and any persisted serialized data.
- Trait method renames break all `impl` blocks silently until compilation; there is no deprecation path for trait methods, so plan for a coordinated rename.
- `#[repr(C)]` struct field reordering changes the ABI and breaks any FFI or unsafe transmutes; treat these as unsafe changes requiring explicit documentation.
