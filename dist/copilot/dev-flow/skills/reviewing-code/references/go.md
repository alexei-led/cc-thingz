# Go Review Reference

Host skill owns scope, severity, scoring, and output. This file adds Go-specific evidence gathering and checks.

## Tool-enabled review

Run configured project tools only when the active role can execute commands. Prefer project commands when present.

Useful Go gates:

```bash
go build ./...
go vet ./...
go test -race -short ./...
golangci-lint run ./...
```

Treat tool output as evidence, then map it through the severity rubric. If a tool is missing or too slow, report the gap and continue source review. Do not install tools.

## Read-only review

When commands are unavailable, use supplied diff, file reads, and any caller-supplied tool output. Follow direct callers for changed exported functions, interface implementations, context use, and resource ownership.

## Focus checks

Correctness:

- Nil pointer, nil map, nil channel, or nil interface paths.
- Off-by-one slice or loop boundaries.
- Integer overflow or truncation in sizes, indexes, money, or time.
- Ignored errors, wrong error wrapping, or swallowed cancellation.
- Interface contract mismatch between implementation and caller.

Security:

- SQL or command injection from string-built queries or shell commands.
- Path traversal from untrusted file paths.
- Weak randomness or crypto for secrets.
- Secret exposure in logs, errors, config, or responses.
- Authorization checks missing at concrete handlers or service boundaries.

Reliability:

- Missing context propagation or timeout on external calls.
- Goroutine leaks, unbounded goroutines, channel deadlocks, or data races.
- Missing `Close` on files, connections, response bodies, rows, or statements.
- Retry loops without backoff, cap, or idempotency check.

Performance:

- N+1 queries or serial external calls on realistic collections.
- `defer` in hot loops.
- Repeated string concatenation in loops.
- Avoidable allocations in hot paths only when the path is plausible.

Tests:

- Changed behavior without table coverage for success, failure, and edge cases.
- Concurrency changes without race-sensitive tests or race-detector evidence.
- Tests coupled to private helpers instead of exported behavior.

## Version-gated checks

Inspect `go.mod`, toolchain, and CI before applying version-specific claims.

- Go 1.22 and later fixed loop variable capture semantics; do not flag old guidance unless the code still has a clarity or compatibility issue.
- Go 1.25 vet can catch more WaitGroup and host-port issues; cite tool output if available.

## Failure handling

- Build, vet, or race failure in reviewed scope: Critical when confirmed by output.
- Linter warning: severity depends on impact; do not auto-promote to Critical.
- Security context missing: use Needs review and name the missing caller, config, or trust boundary.
- LSP or graph unavailable: note reduced cross-file coverage only if it affects the finding.
