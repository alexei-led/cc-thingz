# Code Comments and API Docs

Read when the change touches code comments, docstrings, public API docs, or code
examples.

## All languages

- Public API docs state what the name and types do not: behavior, constraints,
  errors, side effects, concurrency, and compatibility. Follow the project's
  existing doc style.
- Keep comments that explain why: invariants, business rules, external limits,
  ordering requirements, workarounds, and deliberate suppressions (`unsafe`, `!`,
  `#[allow]`, casts). Delete comments that restate the code.
- Tests explain themselves through names, table cases, and assertions. Comment
  only non-obvious external behavior or why an edge case matters.
- README commands and examples match the current package manager, toolchain, and
  API. Run or compile examples when practical.

## Per language

Prefer the project's configured checks. Use these when the tools exist and the
project has no docs target.

| Language | Doc checks |
| --- | --- |
| Go | `go doc <pkg>`, `golangci-lint run --enable=godot,godoclint,revive ./...` |
| Python | `python -m pydoc <module>`, `sphinx-build -b html docs/ docs/_build/` |
| Rust | `cargo doc --no-deps`, `cargo test --doc` |
| TypeScript / JavaScript | `tsc --noEmit`, `typedoc` when configured |
| C# / .NET | `dotnet build` with `GenerateDocumentationFile` (missing docs warn as CS1591) |
| Java / Kotlin | `./gradlew javadoc`, `./mvnw javadoc:javadoc`, or the project's Dokka task |
| Web (HTML, CSS, HTMX) | `npx html-validate .` |
