---
{"description":"Idiomatic C# /.NET development. Use when writing C# code, changing `.csproj` or `.sln`, or working on ASP.NET Core apps, libraries, CLIs, workers, and xUnit/NUnit/MSTest suites. Emphasizes nullable references, async/await, boundary validation, focused `dotnet` feedback, and minimal dependencies. NOT for Go, Python, TypeScript, shell scripts, or infra-only work.","name":"writing-csharp"}
---
<!-- Codex platform guidance -->
<!-- Use this platform's installed tool names exactly for shell, file reads, and search. If a referenced helper or optional tool is unavailable, say so and continue with built-in tools. -->


# C# /.NET Development

Check the nearest `*.csproj`, `Directory.Build.props`, `global.json`, and CI for `TargetFramework(s)`, `LangVersion`, nullable context, and analyzer policy before using newer syntax. Without an explicit `LangVersion`, the C# version follows the TFM (`net8.0` defaults to C# 12; `net6.0` defaults to C# 10, which lacks primary constructors and collection expressions). Project conventions win over these defaults, and raising `LangVersion` or the TFM to unlock syntax is a separate decision — ask first, don't do it on your own.

## Defaults

- BCL and existing NuGet packages first. Keep the app's existing choices: controllers vs minimal APIs, DI container, ORM, test framework.
- Nullable reference types stay on. Model absence with `?`; handle a missing result explicitly (e.g. return `NotFound`/`Problem`) instead of `!`. Never suppress a warning; fix it at the source.
- Async end to end: no `.Result`, `.Wait()`, or `GetAwaiter().GetResult()`. Pass `CancellationToken` through cancellable boundaries, including EF calls.
- Never let a singleton capture a scoped service (e.g. a `DbContext`); use `IServiceScopeFactory` or `IDbContextFactory` when a singleton needs scoped data.
- Validate request DTOs and message payloads at the handler before mapping to domain types; model binding alone is not validation. Return response DTOs from API boundaries, not entities.
- Bind and validate options at startup (`ValidateOnStart`); inject typed options instead of reading config ad hoc.
- Background services honor the stopping token; replace `Thread.Sleep` with a cancellable wait (`Task.Delay` with the token, or `PeriodicTimer`).

## CLIs

- Existing CLI stack first; the BCL is enough for small tools. Add `System.CommandLine` or Spectre.Console only when the command surface justifies it.
- `Program.cs` only calls a `Run(args, stdout, stderr)` seam and returns its exit code; parsing, execution, and error handling (including try/catch) live inside `Run`, not in `Program.cs`.
- Test `Run` with `dotnet test --filter` for exit code and output, including a non-zero exit and a stderr message on bad input.

## References

- [testing.md](references/testing.md): read when adding or reshaping tests, or when `dotnet test` is slow.
- [linting.md](references/linting.md): read when changing `dotnet format`, analyzers, or warning policy.

Done when the relevant build/test/lint checks pass on what you changed, or you name each check that did not run and why.
