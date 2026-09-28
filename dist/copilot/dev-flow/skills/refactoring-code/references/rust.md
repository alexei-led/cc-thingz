# Rust Refactoring Caveats

- rust-analyzer rename stops at the workspace; search dependent crates separately.
- Module moves: update `mod` declarations, `use` paths, `pub use` re-exports, and `#[path]` or `include!` overrides.
- Renaming a public item in a published crate is semver-breaking; keep a deprecated re-export.
- Renaming a field or variant changes its serde key unless `rename`/`rename_all` pins it; check persisted data.
- Trait methods have no deprecation path; rename every `impl` and bound in one batch.
- Reordering `#[repr(C)]` fields changes the ABI and breaks FFI or transmutes; treat it as an unsafe change.
