# Official Documentation Source Map

Use this after Context7 fails or when canonical ecosystem docs are a better fit.
Prefer the exact installed version. Use web tools for discovery only; ground final
claims in primary URLs.

## Version Evidence

Find versions from local manifests, lockfiles, package-manager output, build-tool
metadata, or environment metadata. Account for overrides, replacements, features,
BOMs, preview SDKs, and local forks. If no local version is available, say
`version unknown`; do not invent one.

## General Order

1. Language or platform official docs for standard library and core APIs.
2. Official ecosystem registry for package identity, versions, metadata, and docs
   links.
3. Official project docs linked from the registry or project homepage.
4. GitHub releases, tags, README, `/docs`, examples, source, or tests only when
   docs are missing, incomplete, or version-mismatched.

## JavaScript and TypeScript

Primary sources:

- MDN for Web APIs and core JavaScript language behavior.
- Node.js official docs for Node APIs.
- TypeScript docs and release notes for TypeScript language/compiler behavior.
- npm package page for versions, dist-tags, dependencies, homepage, repository,
  and docs links.
- Official framework/library docs linked from npm or the repo.

## Python

Primary sources:

- `docs.python.org` for Python language, standard library, packaging tools, and
  version-specific "What's New" changes.
- PyPI package page for versions, dependencies, classifiers, project URLs,
  documentation, homepage, and repository links.
- Project docs linked from PyPI or the project homepage, often Read the Docs,
  Sphinx, or MkDocs.

## Go

Primary sources:

- `pkg.go.dev` for package docs generated from Go comments, exported types,
  functions, methods, examples, and version-specific module pages.
- Official Go docs for language spec, standard library, tools, modules, and
  release notes.
- Project docs linked from `pkg.go.dev` for guides and examples.

## Rust

Primary sources:

- `docs.rs` for Rustdoc API documentation by crate version and enabled features
  when available.
- `crates.io` for versions, features, dependencies, documentation, homepage, and
  repository links.
- Project docs linked from `crates.io` for guides or unstable APIs.

## Java and Kotlin

Primary sources:

- Official Java SE/OpenJDK docs for JDK APIs.
- Maven Central for coordinates, versions, POM metadata, homepage, SCM, and docs
  links.
- Official Javadoc and reference docs for the library/framework.
- Framework docs for Spring, Jakarta EE, Android, Kotlin, Gradle, and Maven.

## .NET

Primary sources:

- Microsoft Learn and the .NET API browser for .NET runtime, BCL, ASP.NET,
  Entity Framework, C#, F#, and first-party packages.
- NuGet package page for versions, target frameworks, dependencies, docs,
  project URL, license, and repository links.
- Official third-party docs linked from NuGet or the project homepage.

## Other Ecosystems

Use the same pattern:

- Ruby: Ruby docs and stdlib docs first; RubyGems for metadata; project docs or
  GitHub tags next.
- PHP: PHP manual first; Packagist for package metadata; project docs or GitHub
  tags next.
- Elixir/Erlang: HexDocs and Hex package metadata first; GitHub tags next.
- Swift: Apple Developer Documentation first; Swift Package Index and project
  docs next.
- C/C++: official project docs, package manager metadata, release notes, and
  headers/source at the matching tag when needed.

## GitHub Fallback Rules

Use GitHub as a precise fallback, not a default summary source:

1. Confirm the repository from registry metadata or official docs.
2. Prefer the tag matching the installed version.
3. Read `CHANGELOG*`, `RELEASE*`, `MIGRATION*`, `README*`, `/docs`, and examples
   before source when available.
4. Use source/tests only to confirm undocumented behavior or signatures.
5. Cite the tag, file path, and relevant line or section when possible.
6. If only `main` has docs, say it may not match the installed version.
