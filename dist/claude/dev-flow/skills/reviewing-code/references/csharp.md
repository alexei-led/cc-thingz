# C# /.NET Review Focus

Use writing-csharp for toolchain commands.

- Nullable warnings hidden with `!`, suppressions, or broad defaults instead of fixing the source.
- Sync-over-async (`.Result`, `.Wait()`), missing `await`, `async void` outside event handlers.
- LINQ deferred execution: repeated enumeration, wrong cardinality (`First` vs `Single`), client-side evaluation.
- `CancellationToken` not propagated to external I/O.
- Scoped services captured by singletons; shared mutable state across requests.
- Auth or ownership missing at controllers, minimal APIs, gRPC handlers, or worker entry points.
- Background services without bounded retries, shutdown handling, or idempotency.
- Build, test, or analyzer failure in scope is Critical when output confirms it.
