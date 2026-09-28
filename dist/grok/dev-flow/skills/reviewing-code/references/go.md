# Go Review Focus

Use writing-go for toolchain commands. Check `go.mod` and CI before any
version-gated claim.

- Nil interfaces holding typed nil pointers; nil map writes; sends on nil or closed channels.
- Errors ignored, wrapped without `%w`, or cancellation swallowed; `context` not passed to external calls.
- Goroutines without an exit path, unbounded fan-out, `WaitGroup` misuse, shared maps written without sync.
- Missing `Close` on response bodies, rows, statements, and files, especially on error branches.
- `defer` inside hot loops; serial external calls over collections.
- Concurrency changes need `-race` evidence or race-sensitive tests.
- Go 1.22+ fixed per-iteration loop variables; flag capture bugs only in older modules.
- Build, vet, or race failure in scope is Critical when output confirms it.
