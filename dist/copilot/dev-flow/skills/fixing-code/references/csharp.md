# C# /.NET fix reference

Use for C# and .NET defect fixes. The host skill owns the full fix workflow; this file adds language-specific repro commands and key failure patterns.

## Repro and narrow loop

Find the fastest reliable failing signal first:

```bash
dotnet build path/to/App.sln
dotnet test path/to/Tests.csproj -v quiet
dotnet test path/to/Tests.csproj --filter "FullyQualifiedName~ClassName"
dotnet format path/to/App.sln --verify-no-changes
```

Use the nearest `*.csproj` or containing `*.sln` as the target. Prefer filtering by test name while editing; run the full project or solution before final output.

## Key failure patterns

- Nullable reference warnings hidden with `!` or `#pragma warning disable` instead of fixing the null source.
- `await` dropped on async methods, causing result to be `Task<T>` instead of `T`.
- Linq query deferred execution causing multiple enumeration or incorrect semantics.
- Missing `CancellationToken` propagation on async paths that hit external services.
- Scoped or transient services captured into singletons causing cross-request leaks.
- `ObjectDisposedException` from disposing a shared resource too early or from the wrong scope.

## Verification

Before claiming fixed:

- Failing test or repro no longer fails.
- `dotnet build` shows no errors or new warnings.
- `dotnet format --verify-no-changes` exits clean.
- If the fix changes public API, check callers with `dotnet build` on the containing solution.
