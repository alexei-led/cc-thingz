# Go Linting

Use before changing Go lint commands, golangci-lint config, vet flow, or
lint-heavy verification.

## Fast feedback

- Use the project lint command first.
- Prefer linting the changed package or package tree when supported.
- Prefer cheap built-in checks for the edit loop when they catch the issue:

```bash
gofmt -w file.go
go test ./pkg/name
go vet ./pkg/name
golangci-lint run ./pkg/name
```

- Keep race, coverage, and full repository lint out of the every-turn loop unless
  they are the failing signal.

## golangci-lint

- Preserve the golangci-lint cache. Do not run cache clean as a routine fix.
- Use `--fast-only` only for an explicit hot-path command; run the full configured
  linter set before final output or in CI.
- Let golangci-lint choose concurrency unless measurement shows a problem. It can
  set concurrency from container CPU quota and logical CPUs.
- Avoid running multiple golangci-lint instances in the same repo at once unless
  the project explicitly supports that workflow.
- Keep generated, vendor, fixtures, and build output excluded through normal
  config rather than ad hoc command filters.

## Do not weaken signal

- Do not disable linters or loosen rules just to make the command faster.
- If one linter dominates runtime, report the bottleneck and propose a split
  between hot-path and full-gate commands.
- Keep lint and format separate when that gives faster focused feedback.
