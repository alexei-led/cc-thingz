# C# /.NET Test Slice

Use this only for C# test work. The host skill owns scope, workflow, and output.

## Commands

Use project commands first. If none exist, choose the narrowest useful command:

```bash
dotnet test path/to/Tests.csproj
dotnet test path/to/App.sln
dotnet test path/to/App.csproj
```

Keep the edit loop focused on the nearest useful test project or containing
solution. Run a broader solution command before final output when the change
crosses project boundaries.

## Learn project patterns

Before changing tests:

- Read 2-3 nearby test files.
- Check shared fixtures, test hosts, factory helpers, and project-specific harnesses.
- Follow the existing xUnit, NUnit, or MSTest style unless it is the problem.

## Behavior seams

Prefer public handlers, APIs, services, commands, or library entry points. Use
narrower seams only when behavior is pure, local, deterministic, and cheap.

## Fast feedback defaults

- Keep browser, end-to-end, coverage, and slow integration tiers off the hot path unless they are the task.
- Use parameterized tests when cases share setup and assertions.
- Use `async Task` tests for async code. Do not use `async void` tests.
- Avoid real sleeps; use deterministic synchronization, controlled clocks, or polling helpers with hard timeouts.

## Mocks and integration seams

- Mock only system boundaries: network, filesystem, time, randomness, subprocesses, databases, and external services.
- Prefer real domain collaborators or small fakes when they are cheaper and clearer.
- For ASP.NET Core, use the project's existing HTTP or host harness before adding a new one.
- For EF-backed code, prefer the project's real persistence seam over mocking LINQ providers.

## Review focus

Flag:

- tests coupled to internals instead of observable behavior
- happy-path-only coverage for meaningful logic
- missing nullability, error, cancellation, permission, or regression cases
- repeated setup or heavyweight fixtures that slow focused runs
- mock setups that hide contracts or accept any business value
- real sleeps, shared mutable state, or order dependencies that create flakes

## Failure handling

- Test runner failures are blocking.
- If no test project is obvious for a source edit, use the containing solution as the safe fallback.
- If no .NET test target exists, report that before other findings.
