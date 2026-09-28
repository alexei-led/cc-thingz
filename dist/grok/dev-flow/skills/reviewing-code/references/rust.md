# Rust Review Focus

Use writing-rust for toolchain commands. Check the `Cargo.toml` edition,
`rust-toolchain.toml`, MSRV, and enabled features before any version-gated claim.

- `unsafe` without a documented soundness invariant is Critical; FFI that assumes C ownership or alignment without proof.
- `unwrap`/`expect` on paths that can fail; `?` where the error should be handled locally.
- Integer overflow wraps silently in release; `as` casts that truncate sizes, offsets, or indexes.
- Blocking calls or `std::sync::Mutex` guards held across `.await`; missing cancellation or timeouts on tasks.
- Secrets exposed through derived `Debug`; non-CSPRNG randomness for tokens.
- Clones in hot paths where a borrow or `Cow` works; unbounded channels.
- Edition 2024 changes `unsafe` rules; do not judge one edition by the other's rules.
- `cfg` and feature flags can hide live code; check enabled features before calling code dead.
- Concurrency or `unsafe` changes need Miri or loom evidence when the project configures them.
