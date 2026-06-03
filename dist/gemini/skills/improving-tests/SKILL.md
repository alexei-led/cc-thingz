---
description: Improve test design and coverage with behavior-focused tests, useful
  seams, characterization tests, TDD, and test refactoring. Use when improving tests,
  adding coverage, refactoring brittle tests, removing test waste, or working test-first.
  NOT for fixing production bugs (use fixing-code), production-code refactors (use
  refactoring-code), or reviewing non-test code quality (use reviewing-code).
name: improving-tests
---

# Test Improvement

Improve tests so they catch real behavior regressions without blocking safe code
changes. Coverage is a signal, not the goal.

## Role-gated action

Detect capability from tools:

- Write-capable role: inspect tests, apply changes, and run verification.
- Read-only role: inspect supplied files/output and emit changes in the Proposed Changes contract. Apply nothing; run nothing.

## Route elsewhere

Do not use this for:

- production bug fixes → `fixing-code`
- production-code refactors → `refactoring-code`
- non-test code review → `reviewing-code`
- new feature implementation unless the user asked for TDD

## References

Detect languages from files in scope and read only the matching reference:

- Go → `references/go.md`
- Python → `references/python.md`
- TypeScript → `references/typescript.md`
- Web → `references/web.md`

Use generic rules only for unsupported languages.

## Modes

- `review`: find weak, duplicate, brittle, missing, slow, or flaky tests
- `refactor`: simplify tests without changing covered behavior
- `coverage`: add tests for uncovered business behavior or error paths
- `tdd`: one red-green-refactor slice at a time
- `full`: review, refactor, and add coverage

## Choose the seam

Test through the contract that users or adjacent modules rely on:

- Public module, package, API, CLI, component, or service boundary.
- Integration seam when behavior depends on real wiring: database, filesystem, HTTP, queue, cache, framework routing, serialization, or config.
- Unit seam when behavior is pure, local, deterministic, and cheap to exercise.

Use graph tools when they help choose the seam or risk:

- GitNexus: use query/context to find flows around a behavior; use impact or detect-changes to choose regression tests for changed symbols and affected processes.
- codegraph: check status first; if fresh, use affected/context to find callers, high fan-in surfaces, and modules that need regression coverage.
- Stale graph indexes are not evidence. Refresh if allowed; otherwise report the gap and use search, coverage output, and source reads.

## Test rules

- Test behavior, not private helpers, call counts, or layout.
- Mock only system boundaries: network, clock, randomness, filesystem, subprocesses, external services.
- Prefer real collaborators or in-memory fakes for internal domain code.
- Cover success, failure, edge, boundary, and regression cases that matter.
- Use coverage to find gaps; do not write low-value assertions just to raise a number.
- Delete shallow or duplicate tests once stronger public-boundary tests cover the behavior.
- Extract helpers only after repeated setup or assertions make tests harder to read.

## TDD and characterization

TDD:

1. Name one behavior at the public seam.
2. Write one failing test that fails for the expected reason.
3. Implement the smallest passing code.
4. Refactor only while green.
5. Repeat one behavior at a time.

Characterization tests:

- Use before risky changes to legacy or under-specified code.
- Capture current externally visible behavior, including quirks.
- Place tests at the public boundary first; add narrower tests only when they add diagnostic value.

## Review checks

Look for:

- tests coupled to private helpers, internals, or incidental call order
- mocks hiding real behavior or contracts
- duplicate scenario matrices that should be parameterized
- missing business, error, edge, concurrency, or permission cases
- flaky tests from time, randomness, ordering, shared state, or real external services
- slow tests that could move down a seam without losing confidence
- dead tests that cover deleted behavior or generated glue

Preferred consolidation:

- Go: table-driven tests with subtests.
- Python: parametrized pytest cases.
- TypeScript: `it.each` or equivalent project pattern.

## Verification

Run the relevant project command after changes. Examples:

```bash
go test ./...
pytest -v
bun test
```

Use coverage commands only when coverage mode or review needs them. Report skipped
checks with reasons.

## Output

Engineer:

```text
TEST IMPROVEMENT COMPLETE
=========================
Mode: review | refactor | coverage | tdd | full
Tests changed: N
Waste removed: N
Coverage: before → after | not measured
Status: CLEAN | NEEDS ATTENTION

Key improvements:
- path:line — change

Verification:
- <command> — pass/fail
```

Reviewer:

```text
## Proposed Changes

### Change 1: <brief description>

File: `path/to/test_file`
Action: CREATE | MODIFY | DELETE

Code:
<complete test code or changed region with enough context>

Rationale: <weak, missing, brittle, slow, or duplicate test this fixes>
Verification: <command the applier should run>
```

If no test framework exists, ask before adding one.
