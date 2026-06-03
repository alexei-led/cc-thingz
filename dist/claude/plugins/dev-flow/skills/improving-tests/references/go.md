# Go Test Slice

Use this only for Go test work. The host skill owns scope, workflow, and output.

## Commands

Use project commands first. If none exist, choose the narrowest useful command:

```bash
go test ./...
go test -race ./...
go test -coverprofile=/tmp/coverage.out ./... && go tool cover -func=/tmp/coverage.out
golangci-lint run ./...
```

Run coverage only for coverage mode or when review needs it. If `golangci-lint` or
coverage tooling is unavailable, quote the error and continue with source/test reads.

## Learn project patterns

Before changing tests:

- Read 2-3 nearby `*_test.go` files.
- Check shared helpers, `testdata/`, fixtures, and generated mocks.
- Follow existing assert, require, mock, and table conventions unless they are the problem.

## Behavior seams

Prefer public package, API, CLI, or service boundaries. Use narrower unit seams
only when behavior is pure, local, deterministic, and cheap.

If setup needs many mocks or globals, report the design smell. Do not refactor
production code unless the selected TDD slice requires it and the user approved it.

## Table-driven tests

Prefer table-driven tests when cases share setup and assertions. Do not force a
table when separate tests make distinct behavior clearer.

Good tables include:

- descriptive `name`
- success, failure, edge, boundary, and regression cases that matter
- `t.Run(tc.name, ...)`
- `t.Parallel()` only when cases are truly independent

Keep tables readable. Split very large or unrelated matrices.

## Assertions and mocks

- Use `require` for setup/preconditions that must stop the test.
- Use `assert` for independent result checks when the project already uses testify.
- Check errors before dereferencing values.
- Mock system boundaries, not internal collaborators when real objects are cheap.
- Prefer exact values for business-critical args.
- Use loose matchers such as `mock.Anything` only for contexts, loggers, tracers, or true don't-care values.

Follow project mock-generation conventions. Use mockery only when the repo already
uses it or the user approves adding it.

## Review focus

Flag:

- private-helper tests that miss public behavior
- happy-path-only tests for meaningful logic
- duplicate scenarios that can be clearer as a table
- mocks that hide contracts or accept any business value
- missing error, edge, permission, concurrency, or regression cases
- race failures or flaky shared state
- comments that explain obvious test code instead of improving names/setup

## Failure handling

- Race failures are blocking.
- Test failures and coverage gaps belong in findings.
- If tools fail to run, quote output and mark affected checks skipped.
- If no tests exist, report that before other findings.
