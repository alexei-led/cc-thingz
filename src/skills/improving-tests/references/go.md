# Go Tests

Use writing-go for toolchain commands.

## Patterns

- Table-driven tests with a descriptive `name` and `t.Run(tc.name, ...)`; split large or unrelated matrices.
- With testify, `require` for preconditions that must stop the test, `assert` for independent checks. Check errors before dereferencing results.
- `mock.Anything` only for contexts, loggers, and true don't-care values. Use mockery only if the repo already does.
- Setup that needs many mocks or globals is a design smell to report, not to paper over.

## Speed

- Package-list mode (`go test ./pkg/...`) caches passing results; bare `go test` does not. Avoid `-count=1` unless you are chasing a flake or side effect. `-run`, `-short`, `-parallel`, `-failfast`, `-timeout`, and `-v` stay cacheable.
- Tests that read env vars or module files miss the cache when those change.
- `t.Parallel()` only with isolated state. `t.Setenv` is process-wide and panics under parallel tests or parallel ancestors.
- Tune `-parallel` only after measuring; above CPU count it often slows down.
- Replace sleeps with channels, contexts, fake clocks, or `testing/synctest` when the module's Go version supports it.
- Gate real databases, networks, and containers behind `testing.Short()` or build tags.
- `-race`, coverage profiles, and benchmarks are separate tiers, not the edit loop. Race failures are blocking.
