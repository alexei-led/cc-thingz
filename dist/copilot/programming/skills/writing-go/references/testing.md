# Go Testing

## Tools

- Stdlib `testing` by default. Keep testify, mockery, or other helpers only where the project already uses them.
- testify: `require` for prerequisites, `assert` for independent checks. Never call either from a spawned goroutine; `FailNow` must run on the test goroutine.
- Prefer hand-written fakes for private consumer interfaces over generated mocks.
- Mock matchers: match business-critical arguments exactly. Wildcard `context.Context` only when cancellation, deadline, and values are irrelevant. Use predicate matchers for partial structs, SQL, JSON, timestamps, or IDs.
- HTTP handlers: `httptest` at the request/response boundary.
- Put file fixtures under `testdata/`.

## Fast Loop

```bash
go test ./pkg/name
go test ./pkg/name -run 'TestCreate/duplicate'
go test -short ./...
```

- Use package-list mode (`go test ./pkg/name`). Bare `go test` runs in local-directory mode, which disables the result cache.
- Avoid `-count=1` unless you must bypass the cache for side effects or flake diagnosis.
- Gate slow external tiers with `testing.Short()`. Use integration build tags only if the project already splits tiers that way.
- Keep `-race`, coverage, and benchmarks off the hot path. Run `-race` when the change touches goroutines, shared state, timers, or channels.

## Concurrency and State

- Use `testing/synctest` (1.25+) or fake clocks and explicit synchronization. Never assert with sleeps.
- `t.Setenv` and `t.Chdir` panic in parallel tests; process-wide state and `t.Parallel` do not mix.
