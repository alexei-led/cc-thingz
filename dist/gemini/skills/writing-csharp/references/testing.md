# C# /.NET testing

Read before adding or reshaping C# tests.

## Defaults

- Use the project's test framework: xUnit, NUnit, or MSTest. Do not switch frameworks in scoped work.
- Test behavior through public APIs, handlers, services, commands, or other stable seams.
- Cover success, failure, boundary, cancellation, and regression behavior when relevant.
- Keep tests readable without comments.

## Commands

Use project commands first. If none exist, choose the narrowest useful command:

```bash
dotnet test path/to/Tests.csproj
dotnet test path/to/App.sln
dotnet test path/to/App.csproj
```

Keep the edit loop focused on the nearest useful test project or solution.
Use broader solution runs before final output when the change crosses project
boundaries.

## Test style

- Prefer the framework's parameterized-test style for case matrices.
- Use `async Task` tests for async code. Do not use `async void` tests.
- Assert visible behavior, returned values, thrown exceptions, and external side effects.
- Delete shallow duplicate tests once stronger boundary tests cover the same path.

## Mocks and integration seams

- Mock only system boundaries: network, filesystem, time, randomness, subprocesses, databases, and external services.
- Prefer real domain collaborators or small fakes when they are cheaper and clearer than mocks.
- For ASP.NET Core HTTP behavior, use the project's existing integration-test harness before adding a new one.
- For EF-backed code, prefer disposable test databases or the project's existing test seam over mocking IQueryable chains.

## Fast feedback

- Keep browser, end-to-end, coverage, and slow integration tiers off the hot path unless they are the task.
- Avoid real sleeps; use controlled clocks, cancellation, polling helpers, or deterministic synchronization.
- Keep shared fixtures small enough that focused runs stay focused.
- Run the broader configured suite before final output when the change affects multiple projects or boundaries.
