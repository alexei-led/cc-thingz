---
{"description":"Idiomatic C# /.NET development. Use when writing C# code, changing `.csproj` or `.sln`, or working on ASP.NET Core apps, libraries, CLIs, workers, and xUnit/NUnit/MSTest suites. Emphasizes nullable references, async/await, LINQ discipline, boundary validation, focused `dotnet` feedback, and minimal dependencies. NOT for Go, Python, TypeScript, shell scripts, or infra-only work.","name":"writing-csharp"}
---
<!-- Codex platform guidance -->
<!-- Use this platform's installed tool names exactly for shell, file reads, and search. If a referenced helper or optional tool is unavailable, say so and continue with built-in tools. -->


# C# /.NET Development

Check the nearest `*.csproj`, `Directory.Build.props`, `global.json`, and CI for `TargetFramework(s)`, `LangVersion`, nullable context, and analyzer policy before using newer APIs or syntax. Project conventions win over these defaults.

## Defaults

- BCL and existing NuGet packages first. Keep the app's existing choices: controllers vs minimal APIs, MediatR or none, EF vs Dapper vs raw SQL, the configured test framework.
- Keep nullable reference types on. Model absence with `?`; do not scatter `!` or suppress warnings.
- Async end to end. Never block with `.Result`, `.Wait()`, or `GetAwaiter().GetResult()`. Pass `CancellationToken` through cancellable boundaries. `ValueTask` only when an existing API or a measurement calls for it.
- Materialize LINQ once where it is needed; avoid repeated `ToList()` and multi-pass chains on hot paths.
- Built-in DI unless the project chose another container. No interface per class. Never let a singleton capture a scoped service or request state.
- Validate request DTOs and message payloads at the handler before mapping to domain types; model binding alone is not validation.
- Bind and validate options at startup; inject typed options instead of reading config ad hoc.
- Keep EF queries in repositories or adapters, project only needed fields on reads, and handle transactions and concurrency tokens at the persistence edge.
- Background services honor the stopping token and keep retry and backoff in one place.
- XML docs on public APIs when the project emits docs or enforces CS1591.

## CLIs

- Existing CLI stack first; the BCL is enough for small tools. Add `System.CommandLine` or Spectre.Console only when the command surface justifies it.
- Keep `Program.cs` thin. Test the handler or a `Run(args, stdout, stderr)` seam and assert exit code and output.

## References

- [testing.md](references/testing.md): read when adding or reshaping tests, or when `dotnet test` is slow.
- [linting.md](references/linting.md): read when changing `dotnet format`, analyzers, or warning policy.

Done when the relevant build/test/lint checks pass on what you changed, or you name each check that did not run and why.
