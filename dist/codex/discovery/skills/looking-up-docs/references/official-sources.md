# Official Sources

Tier 2 and Tier 3 details. Prefer docs for the exact installed version.

## Version evidence

Resolve the effective version, not only the declared one: account for
overrides, `replace` directives, enabled features, BOM-managed versions,
preview SDKs, and local forks.

## Version-pinned sources

| Ecosystem   | Version-pinned docs                                           | Registry facts worth checking                       |
| ----------- | ------------------------------------------------------------- | --------------------------------------------------- |
| JS/TS       | Library docs linked from npm; MDN for Web APIs; Node.js docs  | npm dist-tags (`latest` vs `next`), `exports` map   |
| Python      | `docs.python.org` for stdlib; project docs linked from PyPI   | "What's New" pages for stdlib changes by release    |
| Go          | `pkg.go.dev/<module>@<version>`                               | Module major version suffix (`/v2`) changes imports |
| Rust        | `docs.rs/<crate>/<version>`                                   | Items gated behind non-default features             |
| Java/Kotlin | Javadoc for the exact artifact version                        | Maven Central coordinates; BOM-managed versions     |
| .NET        | Microsoft Learn API browser with the version selector         | NuGet target frameworks                             |
| Elixir      | HexDocs for the exact version                                 | Hex package metadata                                |
| Swift       | Apple Developer Documentation; Swift Package Index            | Package platform requirements                       |

## GitHub fallback

1. Confirm the repository from registry metadata or official docs.
2. Read the tag that matches the installed version: `CHANGELOG*`,
   `MIGRATION*`, `README*`, `/docs`, and examples before source.
3. Use source and tests only to confirm undocumented behavior or signatures.
4. Cite the tag, file path, and line or section.
5. If only the default branch has docs, say they may not match the installed
   version.
