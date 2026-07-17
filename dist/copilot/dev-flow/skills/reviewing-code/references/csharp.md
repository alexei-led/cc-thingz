# C# /.NET Review Reference

Host skill owns scope, severity, scoring, and output. This file adds C#-specific
evidence gathering and checks.

## Tool-enabled review

Run configured project tools only when the active role can execute commands.
Prefer project commands when present.

Useful .NET gates:

```bash
dotnet build path/to/App.sln
dotnet test path/to/App.sln
dotnet format path/to/App.sln --verify-no-changes
```

Treat tool output as evidence, then map it through the severity rubric. If a
tool is missing or too slow, report the gap and continue source review. Do not
install tools.

## Read-only review

When commands are unavailable, use supplied diff, file reads, and caller-supplied
output. Follow direct callers for changed public methods, controllers, endpoints,
background workers, repositories, and DTO boundaries.

## Focus checks

Correctness:

- Nullable reference warnings hidden with `!`, suppression, or overly broad null defaults.
- Sync-over-async or missing `await` on real async work.
- Contract mismatch between DTOs, validators, handlers, and callers.
- LINQ queries that change semantics through deferred execution, repeated enumeration, or wrong cardinality assumptions.
- Project or package changes that break build, analyzers, or runtime wiring.

Security:

- Missing auth or ownership checks at controllers, minimal APIs, gRPC handlers, or worker entry points.
- SQL injection from raw SQL or string-built queries.
- Path traversal, command injection, or unsafe file/process handling.
- Secrets in configuration, logs, exceptions, or responses.
- Insecure cookie, token, CORS, or data-protection changes.

Reliability:

- Missing `CancellationToken` propagation for external I/O.
- Disposable resources not closed or awaited.
- Background services without bounded retries, shutdown handling, or idempotency.
- Scoped services captured by singletons or shared mutable state across requests.

Performance:

- N+1 queries, repeated enumeration, or unnecessary materialization on realistic paths.
- Blocking I/O in request or worker hot paths.
- Large object churn from avoidable allocations only when the path is plausible.

Tests:

- Changed behavior without xUnit/NUnit/MSTest coverage for success, failure, and edge cases.
- Bug fixes without a regression test at the public seam.
- Tests coupled to internals instead of observable behavior.

## Failure handling

- Build, test, or analyzer failure in reviewed scope: Critical when confirmed by output.
- Ambiguous framework or auth behavior: use Needs review and name the missing boundary or configuration.
- If graph or LSP evidence is unavailable, note reduced cross-file coverage only when it affects the finding.
