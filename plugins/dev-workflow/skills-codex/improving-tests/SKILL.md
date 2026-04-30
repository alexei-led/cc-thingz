---
name: improving-tests
description: Improve test design and coverage, including TDD/red-green-refactor guidance. Use when improving tests, refactoring tests, adding coverage, using TDD, or removing test waste.
---

# Test Improvement

Improve tests by making them behavioral, lean, and useful.

## Modes

- `review` → identify weak, duplicate, brittle, or missing tests
- `refactor` → combine to table-driven/parametrized/test.each, remove waste
- `coverage` → add tests for uncovered business behavior
- `tdd` → red-green-refactor loop for a feature or bug
- `full` → review + refactor + coverage

## Testing principles

- Test behavior through public interfaces, not implementation details.
- The module interface is the test surface.
- Mock only system boundaries: external APIs, network, time, randomness, filesystem, subprocesses.
- Do not mock your own internal collaborators just to make tests easy.
- Prefer integration-style tests when they give a clear, stable signal.
- Delete old shallow tests once deeper interface tests cover the behavior.
- No pointless tests for getters, constructors, default props, or generated glue.

## TDD workflow

Use this for test-first or red-green-refactor work.

1. Confirm the public interface and first behavior.
2. Write one failing test for one behavior.
3. Run it and watch it fail for the expected reason.
4. Implement the smallest code that passes.
5. Run the narrow test.
6. Repeat one vertical slice at a time.
7. Refactor only when green.

Do not write all tests first. Bulk RED creates imagined tests coupled to guessed implementation.

## Review workflow

Explore the existing test suite:

```bash
# Go
go test -coverprofile=/tmp/cc-cov.out ./... && go tool cover -func=/tmp/cc-cov.out

# Python
pytest --cov=. --cov-report=term-missing

# TypeScript
bun test --coverage
```

Look for:

- tests coupled to private helpers or call counts
- tests that should be table-driven / parametrized / `test.each`
- duplicate scenarios
- weak mocks hiding real behavior
- missing success, error, and edge cases on business logic
- no usable seam for testing real behavior

## Preferred consolidation patterns

| Language   | Pattern                                          |
| ---------- | ------------------------------------------------ |
| Go         | table-driven with `t.Run(tc.name, ...)`          |
| Python     | `@pytest.mark.parametrize` with `pytest.param()` |
| TypeScript | `it.each([{ input, expected, name }])`           |

Extract helpers only after 3+ repetitions and only when the helper improves readability.

## Verify and report

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
