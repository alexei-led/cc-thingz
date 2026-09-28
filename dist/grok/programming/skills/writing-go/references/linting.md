# Go Linting

Use the project lint command first. Edit loop, scoped to the changed package:

```bash
gofmt -w file.go
go vet ./pkg/name
golangci-lint run ./pkg/name
```

- Run the full configured golangci-lint set before finishing. `--fast-only` belongs only in an explicit hot-path command.
- Keep the golangci-lint cache; `golangci-lint cache clean` is not a routine fix.
- Let golangci-lint choose concurrency (it reads container CPU quota). Do not run two instances in one repo at once.
- Exclude generated, vendor, and fixture code in config, not with ad hoc command filters.
- Do not disable linters or loosen rules for speed. If one linter dominates runtime, propose a hot-path versus full-gate split.
