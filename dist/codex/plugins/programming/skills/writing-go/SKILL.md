---
description: Idiomatic Go development. Use when writing Go code, designing APIs, reviewing
  Go implementations, or changing Go tests. Follow the module's target Go version.
  Prefer stdlib, concrete types, explicit errors, context propagation, fast feedback,
  and behavior tests. NOT for Python, Rust, TypeScript, shell scripts, or infra-only
  work.
name: writing-go
---

# Go Development

Use only for Go modules. Follow the module's target Go version.

## Read First

Read [principles.md](references/principles.md) before writing, changing, or reviewing Go code. Read conditional references only when the change touches that area.

## Conditional References

- [patterns.md](references/patterns.md) — package layout, interfaces, errors, HTTP/service boundaries, concurrency, comments.
- [testing.md](references/testing.md) — adding or reshaping Go tests; keep the local test loop fast.
- [linting.md](references/linting.md) — changing lint config, lint commands, or slow lint workflows.
- [cli.md](references/cli.md) — writing or changing Go CLIs.

## Version-Gated APIs

- Confirm `go.mod`, `toolchain`, CI, and nearby code before using version-specific APIs.
- Go 1.25+: use `sync.WaitGroup.Go` when no error propagation is needed.
- Use existing `errgroup` for goroutine errors or shared cancellation; add it only when the dependency is justified.
- Go 1.25+: use `testing/synctest` for deterministic concurrent tests when available.
- Go 1.25+: prefer stdlib `crypto/hpke` and `testing/cryptotest` over third-party code when they fit.
- Treat `encoding/json/v2` as experimental unless the project opts into `GOEXPERIMENT=jsonv2`.
- Go 1.26+: use `new(expr)` only when clearer than a local variable, composite literal, or address expression.
- Go 1.26+: keep recursive type constraints in generic libraries; keep business logic concrete.

## Verification

Run focused package tests and lint while editing, then the project-configured build, tests, lint, vet, and formatting checks before final output. Add race or concurrency-specific checks when the change touches goroutines, shared state, timers, or channels.

If a check is unavailable, state that and run the closest configured gate. If a check fails, quote the failure, diagnose the cause, fix one issue, and rerun the relevant check.

## Failure Cases

- No clear Go root: locate `go.mod` before choosing files, commands, or import paths.
- Unknown Go target: inspect `go.mod`, `toolchain`, CI, and lockfiles before using version-specific APIs.
- New dependency requested: confirm stdlib or existing dependencies cannot meet the requirement.
- Broad or risky edit: state the risk and ask before acting. Do not run destructive commands.

## Final Response

Include:

- changed files
- checks run and results
- checks skipped with reasons
- remaining risks or follow-ups
