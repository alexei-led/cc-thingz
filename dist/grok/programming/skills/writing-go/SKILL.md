---
{"description":"Idiomatic Go development. Use when writing Go code, designing APIs, reviewing Go implementations, or changing Go tests. Follow the module's target Go version. Prefer stdlib, concrete types, explicit errors, context propagation, fast feedback, and behavior tests. NOT for Python, Rust, TypeScript, shell scripts, or infra-only work.","name":"writing-go"}
---

# Go Development

Check `go.mod` (`go` and `toolchain` lines) and CI before using version-gated APIs. Project conventions win over these defaults.

## Defaults

- Stdlib first: `net/http`, `testing`, `flag`, `log/slog`. Add a module only for a concrete requirement.
- Concrete types in domain code. Consumers own small private interfaces; producers return concrete types.
- Keep HTTP, CLI, database, and vendor SDK types out of domain packages. Map errors to status, exit code, or retry at the edge.
- New binaries: `cmd/<name>` plus `internal/`. Use `pkg/` only for code meant for external import.
- Avoid package stutter: `user.Store`, not `user.UserStore`.
- Doc comments on exported names start with the identifier and end with a period.
- Every goroutine has an owner, a cancellation path, and a completion path. Use `errgroup` for errors or shared cancellation when the module already has it.

## Version-Gated

- 1.24+: `t.Context()`, `t.Chdir()`, and `b.Loop()` in tests.
- 1.25+: `sync.WaitGroup.Go` when no error propagation is needed; `testing/synctest` for deterministic goroutine and timer tests.
- 1.26+: stdlib `crypto/hpke`; `new(expr)` only when clearer than a local variable or composite literal; self-referential generic constraints belong in generic libraries, not business logic.
- 1.26+: `testing/cryptotest.SetGlobalRandom` swaps process-wide randomness, so never use it in parallel tests.
- `encoding/json/v2` is experimental unless the project builds with `GOEXPERIMENT=jsonv2`.

## CLIs

- Use the existing framework. Otherwise `flag` for single-command tools, Cobra for large command trees with completions, urfave/cli for small multi-command tools. Skip Viper unless already used.
- Keep `main` thin: it calls `run(ctx, args, stdin, stdout, stderr) error` and maps the result to an exit code. Tests call `run`. Avoid `log.Fatal`; it skips deferred cleanup.
- Config precedence: flag, env, config file, default.

## References

- [testing.md](references/testing.md): read when adding or reshaping tests, or when the test loop is slow.
- [linting.md](references/linting.md): read when changing lint commands or golangci-lint config.

Done when the relevant build/test/lint checks pass on what you changed, or you name each check that did not run and why.
