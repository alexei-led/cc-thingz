# Test Improvement

Follow the base skill. This Claude overlay only defines tool use and execution details.

Improve tests through public behavior seams. Do not inflate coverage with low-value
assertions. Do not change production behavior unless the selected TDD slice requires it.

## Arguments

- `review`: find weak, duplicate, brittle, missing, slow, or flaky tests.
- `refactor`: simplify tests without changing covered behavior.
- `coverage`: add useful tests for uncovered business behavior or error paths.
- `tdd`: one red-green-refactor slice at a time.
- `full`: review, refactor, and add coverage.

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
2. Load only matching language references.
3. Run the narrow test or coverage command only when it helps the selected mode.
4. Use `Edit` for existing tests and `Write` only for new files.
5. Run the relevant verification before final output.

Use direct reads/search for small scopes. Spawn read-only agents only for broad or
mixed-language audits.

## Command discipline

Use only commands supported by the repo and available tools. Examples:

```bash
go test ./...
go tool cover -func=/tmp/coverage.out
golangci-lint run ./...
pytest -v
uv run pytest -v
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
- Delete shallow duplicates only after stronger public-boundary tests cover them.
- Do not force table-driven, parametrized, or `it.each` consolidation when separate tests make distinct behavior clearer.
- If no safe behavior seam exists, use `BLOCKED` or `Proposed Changes`.

## Output

Use `TEST IMPROVEMENT COMPLETE` for applied changes:

```text
TEST IMPROVEMENT COMPLETE
=========================
Mode: review | refactor | coverage | tdd | full
Tests changed: N
Waste removed: N
Coverage: before → after | not measured
Status: CLEAN | NEEDS ATTENTION

Key improvements:
- file:line — change

Verification:
- <command> — pass/fail/skipped with reason
```

Use `BLOCKED` or `Proposed Changes` when tools, framework, scope, permission, or a
safe seam is missing. Include the exact missing input and the command the applier
should run.

Do not claim clean without a passing check or explicit skipped-check reason.
