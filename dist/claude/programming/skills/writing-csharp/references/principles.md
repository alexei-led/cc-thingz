# C# /.NET principles

Read before writing, changing, or reviewing C# code.

## Project baseline

- Start from the nearest `*.csproj`, `Directory.Build.props`, `global.json`, CI, and nearby code.
- Follow the target framework, SDK, `LangVersion`, nullable context, and analyzer settings already in use.
- Prefer the BCL and existing packages. Add a NuGet package only for a concrete requirement.
- Keep domain logic separate from ASP.NET, EF, configuration, logging, and process wiring.

## Nullability and types

- Keep nullable reference types enabled. Model optional values honestly with `?`.
- Do not blanket-suppress warnings or scatter `!` to silence flow analysis.
- Prefer concrete types for domain code and narrow interfaces at consumers.
- Use records or small immutable types for value data when the project already uses them.
- Validate JSON, HTTP input, env/config, and message payloads before typed domain use.

## Async and LINQ

- Use async end-to-end for I/O. Do not block on `Task.Result`, `Wait()`, or `GetAwaiter().GetResult()`.
- Accept and pass `CancellationToken` on cancellable boundaries.
- Return `Task` or `Task<T>` for async methods. Use `ValueTask` only when an existing API or measurement justifies it.
- Use LINQ when it makes the transform clearer. Avoid multi-pass or allocation-heavy chains in hot paths.
- Materialize once at the boundary that needs it. Avoid repeated `ToList()` or `ToArray()` churn.

## Errors and boundaries

- Keep validation, HTTP status mapping, CLI exit codes, and worker retry policy at the edge.
- Throw specific exceptions with useful context when the project uses exceptions at that boundary.
- Do not leak ASP.NET, EF, or vendor SDK types through stable domain interfaces unless the project already chose that coupling.

## Verification

- Run focused `dotnet test`, `dotnet build`, and `dotnet format` or project equivalents before claiming success.
- If analyzers or warnings fail, fix the cause instead of downgrading the rule.
