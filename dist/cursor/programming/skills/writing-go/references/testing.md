# Go testing

Read before adding or reshaping Go tests.

## Defaults

- Use stdlib `testing` by default. Keep testify, mockery, or other tools only when the project already uses them or they reduce real noise.
- Test behavior through public APIs and stable package boundaries.
- Prefer table-driven tests for input matrices, edge cases, and error variants.
- Cover success, error, boundary, cancellation, and concurrency behavior when relevant.
- Avoid comments in tests. Add one only for unobvious fixtures, timing, concurrency, or regression context.

## Assertions

- Use clear stdlib assertions when they stay readable.
- Use `require` only for prerequisites that make the rest of the test meaningless.
- Use `assert` only for independent checks where seeing multiple failures helps.
- Do not call testify assertions from goroutines.

## Mocks and fakes

- Mock only system boundaries: network, database, filesystem, clock, process, randomness, external services.
- Prefer small hand-written fakes for private consumer interfaces when they are clearer than generated mocks.
- Generate mocks only when the project already uses mockery or the interface has enough reuse to justify it.
- Match business-critical arguments exactly.
- Wildcard context only when cancellation, deadline, and values are irrelevant.
- Use wildcards only for logger, tracer, generated values, or other don't-care inputs.
- Use predicate matchers for structs, SQL, JSON, timestamps, or IDs when only part of the value matters.

## HTTP and integration tests

- Test handlers with `httptest` at the request/response boundary.
- Assert status, headers, response shape, and visible side effects.
- Put external dependencies behind fakes, local test services, or disposable integration fixtures.
- Use integration build tags only when the project already separates slow or external tests that way.

## Fast feedback

- Prefer package-list mode such as `go test ./pkg/name`; bare `go test` disables the successful-result cache.
- Avoid `-count=1` unless bypassing cache is required for side effects or flake diagnosis.
- Use `testing.Short()` and `go test -short` for slow external tiers.
- Keep `-race`, coverage profiles, and benchmarks out of the hot path unless the change touches that risk.

## Concurrency and time

- Use `testing/synctest` for deterministic goroutine and timer tests when the module target supports it.
- Otherwise use fake clocks, channels, contexts, or explicit synchronization.
- Avoid sleeps as assertions. If a timeout is needed, keep it short and tied to failure detection.
- Run race checks for code that touches goroutines, shared memory, timers, or channels.

## Hygiene

- Use `t.Helper`, `t.Cleanup`, and `t.TempDir` for setup helpers and temporary state.
- Use `t.Parallel` only for independent tests with isolated state.
- Do not combine process-wide environment changes with parallel tests.
- Keep table names descriptive and stable.
- Keep fixtures under `testdata` when files are clearer than inline strings.
- Do not test trivial getters, setters, or constructors unless they enforce behavior.
- Delete duplicate shallow tests once a deeper behavior test covers the same case.

## Coverage

- Treat coverage as a signal, not the goal.
- Prioritize regressions, edge cases, and failure paths over line-count padding.
- Do not add tests that only assert implementation details or call counts.
- Do not run coverage in the hot feedback loop unless the task is coverage-specific.
