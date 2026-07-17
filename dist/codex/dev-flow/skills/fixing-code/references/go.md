# Go fix reference

Use for Go defect fixes. The host skill owns the full fix workflow; this file adds language-specific repro commands and key failure patterns.

## Repro and narrow loop

Find the fastest reliable failing signal first:

```bash
go test ./pkg/name -run TestName -v
go test ./pkg/name -run TestName -race
go vet ./...
golangci-lint run ./pkg/name
```

Use the narrowest package and `-run` filter while editing. Run `go test ./...` or the project gate before final output.

## Key failure patterns

- Nil dereference from unchecked error or nil interface return.
- Goroutine leak: goroutine blocked on channel send/receive with no reader or writer; missing context cancellation propagation.
- Unclosed response body, file, rows, or statement causing fd or connection leak.
- Error swallowed silently with `_` or empty `if err != nil { }` branch.
- Data race from shared map, slice, or counter written from multiple goroutines without synchronization.
- Loop variable capture bug in goroutines (pre-1.22 modules only).

## Verification

Before claiming fixed:

- Failing test or repro no longer fails.
- `go vet ./...` exits clean.
- `go build ./...` exits clean.
- For concurrency changes: re-run with `-race` and confirm no data race.
