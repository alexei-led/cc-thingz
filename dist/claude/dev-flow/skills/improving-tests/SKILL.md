---
{"allowed-tools":["Task","TaskOutput","TaskCreate","TaskUpdate","TaskList","Read","Grep","Glob","LS","Edit","Write","AskUserQuestion","Bash(go test *)","Bash(go tool *)","Bash(golangci-lint *)","Bash(pytest *)","Bash(uv run pytest *)","Bash(bun test *)","Bash(bun run *)","Bash(npm test *)","Bash(pnpm test *)","Bash(yarn test *)","Bash(vitest *)","Bash(jest *)","Bash(npx vitest *)","Bash(npx jest *)","Bash(node --test *)","Bash(npx playwright *)","Bash(bunx playwright *)"],"argument-hint":"[review|refactor|coverage|tdd|performance|full]","context":"fork","description":"Improve test design, speed, and coverage with behavior-focused tests, useful seams, characterization tests, TDD, and test refactoring. Use when improving tests, optimizing slow suites, adding coverage, refactoring brittle tests, removing test waste, or working test-first. NOT for fixing production bugs (use fixing-code), production-code refactors (use refactoring-code), or reviewing non-test code quality (use reviewing-code).","name":"improving-tests","user-invocable":true}
---
# Test Improvement

Follow the base skill. This Claude overlay only defines tool use and execution details.

Improve tests through public behavior seams. Treat suite latency as a quality
attribute. Do not inflate coverage with low-value assertions. Do not change
production behavior unless the selected TDD slice requires it.

## Arguments

- `review`: find weak, duplicate, brittle, missing, slow, or flaky tests.
- `refactor`: simplify tests without changing covered behavior.
- `coverage`: add useful tests for uncovered business behavior or error paths.
- `tdd`: one red-green-refactor slice at a time.
- `performance`: measure slow tests and remove speed waste without weakening behavior.
- `full`: review, refactor, performance, and add coverage.

If mode is missing, use `AskUserQuestion` with those options. Ask before adding a
new test framework.

Use `TaskCreate` and `TaskUpdate` when the session has more than two steps:

1. Choose mode and scope.
2. Inspect test structure and project conventions.
3. Select behavior seam.
4. Apply one cluster or one TDD slice.
5. Verify and report.

## Tool order

1. Use `Read`, `Grep`, `Glob`, and `LS` to find tests, fixtures, helpers, and nearby patterns.
2. Load only matching language references. For `performance` mode or slow-suite work, also load the matching `references/<language>-performance.md` when present.
3. Run the narrow test or coverage command only when it helps the selected mode.
4. Use `Edit` for existing tests and `Write` only for new files.
5. Run the relevant verification before final output.

Use direct reads/search for small scopes. Spawn read-only agents only for broad or
mixed-language audits.

## Command discipline

Use only commands supported by the repo and available tools. Examples:

```bash
go test ./pkg -run TestName
go test ./...
go tool cover -func=/tmp/coverage.out
golangci-lint run ./...
vitest run path/to/file.test.ts
jest path/to/file.test.ts --runInBand
pytest -q --maxfail=1 --tb=short
pytest -q --durations=10 --durations-min=0.5
uv run pytest -q --maxfail=1 --tb=short
bun test
bun run tsc --noEmit
npm test
npx playwright test --list
bunx playwright test --list
```

If a referenced command is unavailable, report it as skipped with the exact reason.
Do not install a test framework or tool without user approval.

## TDD mode

For `tdd`, write one failing test for one behavior, confirm it fails for the expected
reason, implement the smallest passing code, then refactor only while green. Do not
write a bulk suite for imagined future behavior.

## Scope control

- Test through public module, package, API, CLI, component, or service boundaries.
- Mock only system boundaries.
- Remove real sleeps, external I/O, broad discovery, repeated setup, and coverage-on-default before reducing checks.
- Delete shallow duplicates only after stronger public-boundary tests cover them.
- Do not force table-driven, parametrized, or `it.each` consolidation when separate tests make distinct behavior clearer.
- If no safe behavior seam exists, use `BLOCKED` or `Proposed Changes`.
