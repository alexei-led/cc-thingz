---
{"description":"Idiomatic C# /.NET development. Use when writing C# code, changing `.csproj` or `.sln`, or working on ASP.NET Core apps, libraries, CLIs, workers, and xUnit/NUnit/MSTest suites. Emphasizes nullable references, async/await, LINQ discipline, boundary validation, focused `dotnet` feedback, and minimal dependencies. NOT for Go, Python, TypeScript, shell scripts, or infra-only work.","name":"writing-csharp"}
---

# C# /.NET Development

Use only for C# and .NET code. Follow the project's SDK, target frameworks,
nullable settings, analyzer config, test stack, and local conventions.

## Read First

Read [principles.md](references/principles.md) before writing, changing, or reviewing C# code. Read conditional references only when the change touches that area.

## Conditional References

- [patterns.md](references/patterns.md) — solution layout, ASP.NET Core boundaries, DI, EF access, config, and worker patterns.
- [testing.md](references/testing.md) — adding or reshaping xUnit, NUnit, or MSTest coverage; keep the local `dotnet test` loop fast.
- [linting.md](references/linting.md) — changing `dotnet format`, analyzers, warning policy, or slow verification flow.
- [cli.md](references/cli.md) — writing or changing .NET CLIs.

## Project Baseline

- Inspect the nearest `*.csproj`, `Directory.Build.props`, `global.json`, solution file, CI, and nearby code before using SDK- or framework-specific APIs.
- Keep nullable reference types enabled. Fix the warning or model, not the warning level.
- Prefer the BCL and existing NuGet packages before adding a dependency.
- Use the existing app style: ASP.NET Core controllers vs minimal APIs, records vs classes, MediatR or no mediator, EF or raw SQL, and the configured test framework.

## Comments and XML Docs

- Use XML documentation comments for public APIs when the project emits API docs or enforces CS1591.
- Summarize contracts, invariants, edge cases, and effects. Do not restate member names or signatures.
- Use `//` for brief implementation notes; avoid long `/* */` explanations.
- Keep comments short. Move longer rationale to docs, issue links, or design notes.
- Do not comment obvious code.
- Keep tests readable without comments; add one only for unobvious fixtures, timing, concurrency, external services, or regression context.

## Verification

Run focused `dotnet` checks while editing, then the project-configured build,
tests, analyzers, and formatting checks before final output. Prefer the
narrowest useful project or solution target for the hot loop, then the broader
configured command before final output.

If a check is unavailable, state that and run the closest configured gate. If a
check fails, quote the failure, diagnose the cause, fix one issue, and rerun the
relevant check.

## Failure Cases

- No clear .NET root: locate the nearest `*.csproj` or containing `*.sln` before choosing files or commands.
- Unknown SDK or language level: inspect `TargetFramework`, `TargetFrameworks`, `LangVersion`, `global.json`, CI, and lockfiles before using newer APIs or syntax.
- New package requested: confirm the BCL or existing packages cannot meet the requirement.
- Broad or risky edit: state the risk and ask before acting. Do not run destructive commands.

## Final Response

Include:

- changed files
- checks run and results
- checks skipped with reasons
- remaining risks or follow-ups