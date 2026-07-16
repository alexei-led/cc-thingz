# Go Test Performance

Use this for `performance` mode or any Go test suite that is too slow for an
agent feedback loop. The host skill owns the generic performance workflow and
quality guardrails. This file adds Go-specific tactics for package selection,
cache use, `testing.Short`, `t.Parallel`, race, coverage, and benchmarks.

## Focused commands

Use project commands first. Examples only:

```bash
go test ./pkg/name -run TestName
go test ./pkg/name -run 'TestName/subcase'
go test -short ./...
go test ./...
go test -race ./pkg/name
go test -coverprofile=/tmp/coverage.out ./pkg/name
```

Use focused package and `-run` commands while editing. Run the broader relevant
package set before final output.

## Use the Go test cache

- Prefer package-list mode such as `go test ./pkg/name` or `go test ./...` over
  bare `go test`; package-list mode caches successful results.
- Do not add `-count=1` unless the task requires bypassing cache for side effects
  or flake investigation.
- Keep cacheable flags cacheable when possible: `-run`, `-short`, `-parallel`,
  `-failfast`, `-timeout`, and `-v` can still use cache.
- If tests read environment variables or files in the module, expect cache misses
  when those inputs change.

## Parallelism and isolation

- Use `t.Parallel()` only for tests and subtests with isolated mutable state.
- Tune `-parallel` only after measuring. Values above available CPUs can degrade
  performance.
- Package-level parallelism is controlled outside the test binary. Avoid forcing
  it higher when packages compete for CPU, databases, ports, or disk.
- Use `t.TempDir`, unique names, and local fixtures. Do not share global mutable
  state between parallel tests.
- `t.Setenv` affects the whole process and is not safe with parallel tests or
  parallel ancestors.

## Remove real-time waits

- Avoid sleeps as assertions.
- Prefer fake clocks, channels, contexts, explicit synchronization, or
  `testing/synctest` when the module target supports it.
- Keep failure timeouts short and tied to diagnosing a stuck goroutine, not to
  proving behavior by waiting.

## Reduce setup and external work

- Use `testdata` for clear file fixtures and `t.TempDir` for per-test copies.
- Build costly immutable fixtures once, then copy or reset them per test.
- Put external services behind fakes, local test services, or explicit
  integration tiers.
- Use build tags or `testing.Short()` for tests that need real databases,
  networks, containers, or slow filesystem trees.

## Keep expensive modes out of the edit loop

- `-race` is required for concurrency risk, but it is too expensive as the
  default every-turn command.
- Coverage profiles are reporting artifacts. Run them for coverage work or final
  gate parity, not every patch attempt.
- Benchmarks answer performance questions; keep them separate from the default
  unit test loop.
