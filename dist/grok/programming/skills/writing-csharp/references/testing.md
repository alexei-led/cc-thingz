# C# /.NET Testing

Use the project's framework (xUnit, NUnit, or MSTest); do not switch in scoped work.

```bash
dotnet test path/to/Tests.csproj --filter "FullyQualifiedName~OrderServiceTests"
dotnet test path/to/Tests.csproj
dotnet test path/to/App.sln
```

- Edit loop: the nearest test project with a `--filter`. Run the solution when the change crosses projects.
- Parameterize case matrices with the framework's style (`[Theory]`, `[TestCase]`, `[DataRow]`).
- Async tests return `async Task`, never `async void`.
- ASP.NET Core HTTP behavior: the project's existing integration harness (usually `WebApplicationFactory`) before a new one.
- EF-backed code: a disposable test database or the project's existing seam, not mocked `IQueryable` chains.
- Replace real sleeps with a controllable clock (.NET 8+: `TimeProvider`, faked with `FakeTimeProvider` from `Microsoft.Extensions.TimeProvider.Testing` when the project accepts that package), cancellation, or deterministic synchronization.
- Keep browser, end-to-end, coverage, and slow integration tiers off the hot path unless they are the task.
