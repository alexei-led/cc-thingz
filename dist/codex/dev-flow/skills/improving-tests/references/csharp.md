# C# /.NET Tests

Use writing-csharp for toolchain commands. Follow the project's xUnit, NUnit, or
MSTest style.

- Iterate on the nearest test project; run the containing solution when the change crosses projects or no test project is obvious.
- Async tests return `async Task`; never `async void`.
- ASP.NET Core: use the project's existing host or `WebApplicationFactory` harness before adding one.
- EF-backed code: test through the real persistence seam (SQLite in-memory or a test container) instead of mocking LINQ providers.
- Cover nullability, cancellation, and permission paths when the code handles them.
- Replace sleeps with deterministic synchronization, a controllable `TimeProvider`, or polling with a hard timeout.
