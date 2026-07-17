# C# /.NET refactoring reference

Use for C# and .NET behavior-preserving refactors. The host skill owns the scope-mapping workflow and output contract; this file adds language-specific mapping tools, safety gates, and caveats.

## Scope mapping

Before editing:

- Use IDE rename/move (Rider, Visual Studio, or Roslyn refactoring in VS Code) for symbol renames — they update all project references including generated code.
- Use `grep`/`rg` or `Find Usages` for string literals, route strings, DI registrations, and reflection-based lookups that static analysis misses.
- For namespace or file moves, check `using` directives in all projects of the containing solution.
- For public API renames, check NuGet consumers across the repo if the package is internal-only; note the breaking change if it is published.

## Verification gate

```bash
dotnet build path/to/App.sln
dotnet test path/to/Tests.csproj
dotnet format path/to/App.sln --verify-no-changes
```

Run build before each batch to catch compile errors early. Run the full test suite before final output.

## Key caveats

- Renaming a public type, member, or namespace is a breaking binary change for external consumers; add `[Obsolete]` shims or version the change.
- Moving a class between namespaces changes its fully qualified name — check reflection, DI container registrations, JSON `$type` discriminators, and mapping configs.
- Extracting an interface changes the DI registration site; update all `AddTransient`/`AddScoped`/`AddSingleton` calls.
- Nullable annotations on refactored methods can silently change callers' null-safety analysis; review `?` and `!` at the new boundary.
- Generated partial classes (Entity Framework, Source Generators, gRPC) should not be hand-edited; change the generator source instead.
