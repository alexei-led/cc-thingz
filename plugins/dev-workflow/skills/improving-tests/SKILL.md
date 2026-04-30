---
name: improving-tests
description: Improve test design and coverage, including TDD/red-green-refactor guidance. Use when user says "improve tests", "refactor tests", "test coverage", "combine tests", "table-driven", "parametrize", "test.each", "test-first", "TDD", "red-green-refactor", or wants to remove test waste.
user-invocable: true
context: fork
argument-hint: "[review|refactor|coverage|tdd|full]"
allowed-tools:
  - Task
  - TaskOutput
  - TaskCreate
  - TaskUpdate
  - TaskList
  - Bash(go test *)
  - Bash(pytest *)
  - Bash(bun test *)
  - Bash(npm test *)
  - Read
  - Grep
  - Glob
  - LS
  - AskUserQuestion
---

# Test Improvement

Improve tests by making them behavioral, lean, and useful. Tests are a design tool, not a line-count sport.

Use TaskCreate / TaskUpdate to track:

1. Choose mode
2. Explore test structure
3. Run coverage or failing-test loop
4. Review with language agent
5. Apply improvements one cluster at a time
6. Verify and report

## Phase 1: Choose Mode

`$ARGUMENTS`:

- `review` → identify weak, duplicate, brittle, or missing tests
- `refactor` → combine to table-driven/parametrized/test.each, remove waste
- `coverage` → add tests for uncovered business behavior
- `tdd` → red-green-refactor loop for a feature or bug
- `full` → review + refactor + coverage
- empty → ask what to do

If empty, ask one question with options: review existing, refactor tests, fill coverage gaps, TDD loop, or full improvement.

## Testing Principles

- Test behavior through public interfaces, not implementation details.
- The module interface is the test surface.
- Mock only system boundaries: external APIs, network, time, randomness, filesystem, subprocesses.
- Do not mock your own internal collaborators just to make tests easy.
- Prefer integration-style tests when they give a clear, stable signal.
- One logical assertion per test case; multiple property checks are fine after one setup.
- Delete old shallow tests once deeper interface tests cover the behavior.
- No pointless tests for getters, constructors, default props, or generated glue.

## Phase 2: Background Exploration

Spawn exploration agents in parallel when available:

```text
Test structure scan:
- Find test files: *_test.go, test_*.py, *.test.ts, *.spec.ts
- Identify frameworks and helpers
- Find table-driven / parametrize / test.each patterns
- Locate mocks, fixtures, integration tests

Coverage analysis:
- Go: go test -coverprofile=/tmp/cc-cov.out ./... && go tool cover -func=/tmp/cc-cov.out
- Python: pytest --cov=. --cov-report=term-missing
- TypeScript: bun test --coverage
```

Exclude generated code, mocks, fixtures, type-only files, and trivial CLI entrypoints from coverage pressure.

## Phase 3: TDD Mode

Use this for `tdd`, `test-first`, or `red-green-refactor` requests.

1. Confirm the public interface and the first behavior.
2. Write one failing test for one behavior.
3. Run it and watch it fail for the expected reason.
4. Implement the smallest code that passes.
5. Run the narrow test.
6. Repeat one vertical slice at a time.
7. Refactor only when green.

Do not write all tests first. Bulk RED creates imagined tests coupled to guessed implementation.

## Phase 4: Review and Improve

Based on language, use the appropriate test agent when available:

- Go → `go-tests`
- Python → `py-tests`
- TypeScript → `ts-tests`
- Web → `web-tests`

Focus findings on:

- tests coupled to private helpers or call counts
- tests that should be table-driven / parametrized / `test.each`
- duplicate scenarios
- weak mocks (`mock.Anything`, unspecced mocks, untyped `vi.fn`) hiding real behavior
- missing success, error, and edge cases on business logic
- no usable seam for testing real behavior

## Phase 5: Apply Improvements

Preferred consolidation patterns:

| Language   | Pattern                                          |
| ---------- | ------------------------------------------------ |
| Go         | table-driven with `t.Run(tc.name, ...)`          |
| Python     | `@pytest.mark.parametrize` with `pytest.param()` |
| TypeScript | `it.each([{ input, expected, name }])`           |

Extract helpers only after 3+ repetitions and only when the helper improves readability. Hide setup noise; do not hide the behavior under test.

## Phase 6: Verify and Report

Run relevant tests:

```bash
go test ./...
pytest -v
bun test
```

Output:

```text
TEST IMPROVEMENT COMPLETE
=========================
Mode: review | refactor | coverage | tdd | full
Tests changed: N
Waste removed: N
Coverage: before → after (if measured)

Key improvements:
- file:line — change

Verification:
- <command> — pass/fail
```

If no tests or framework exist, report that and ask before creating a new testing stack.
