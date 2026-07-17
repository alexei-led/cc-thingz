---
{"description":"Improve test design, speed, and coverage with behavior-focused tests, useful seams, characterization tests, TDD, and test refactoring. Use when improving tests, optimizing slow suites, adding coverage, refactoring brittle tests, removing test waste, or working test-first. NOT for fixing production bugs (use fixing-code), production-code refactors (use refactoring-code), or reviewing non-test code quality (use reviewing-code).","name":"improving-tests"}
---
<!-- Platform guidance for Codex -->
<!-- Use this platform's installed tool names exactly; do not translate capability references into Claude Code tool syntax. -->
<!-- When this skill references shell execution, file reads, or search, use the platform's native shell, read, and search tools. -->
<!-- If a referenced helper command or optional tool is unavailable, report the gap and continue with the platform's built-in tools. -->


# Test Improvement

Improve tests so they catch real behavior regressions without blocking safe code
changes. Suite latency is a quality attribute. Coverage is a signal, not the goal.

## Role-gated action

Detect capability from tools:

- Write-capable role: inspect tests, apply changes, and run verification.
- Read-only role: inspect supplied files/output and emit changes in the Proposed Changes contract. Apply nothing; run nothing.
- Missing key tool or permission: stop with Blocked and ask for the exact artifact, access, or approval needed.

Use an interactive question tool when available for mode selection, missing scope, missing framework approval, or unsafe test-stack choices.

## Route elsewhere

Do not use this for:

- production bug fixes → `fixing-code`
- production-code refactors → `refactoring-code`
- non-test code review → `reviewing-code`
- new feature implementation unless the user asked for TDD
- browser-only UI investigation without a test-improvement goal → `browser-automation`

## References

Detect languages from files in scope and read only the matching reference:

- C# → `references/csharp.md`
- Go → `references/go.md`; for slow-suite or feedback-loop work, also read `references/go-performance.md`
- Java/Kotlin → `references/java-kotlin.md`
- Python → `references/python.md`; for slow-suite or feedback-loop work, also read `references/python-performance.md`
- TypeScript → `references/typescript.md`; for slow-suite or feedback-loop work, also read `references/typescript-performance.md`
- Rust → `references/rust.md`
- Web → `references/web.md`

Use generic rules only for unsupported languages.

## Modes

- `review`: find weak, duplicate, brittle, missing, slow, or flaky tests
- `refactor`: simplify tests without changing covered behavior
- `coverage`: add tests for uncovered business behavior or error paths
- `tdd`: one red-green-refactor slice at a time
- `performance`: measure test latency and remove speed waste without weakening behavior
- `full`: review, refactor, performance, and add coverage

If mode is missing, ask one question with these options.

## Choose the seam

Test through the contract that users or adjacent modules rely on:

- Public module, package, API, CLI, component, or service boundary.
- Integration seam when behavior depends on real wiring: database, filesystem, HTTP, queue, cache, framework routing, serialization, or config.
- Unit seam when behavior is pure, local, deterministic, and cheap to exercise.

Use graph tools only when available and when they help choose the seam or risk:

- GitNexus: use query/context to find flows around a behavior; use impact or detect-changes to choose regression tests for changed symbols and affected processes.
- codegraph: check freshness first; if fresh, use affected/context to find callers, high fan-in surfaces, and modules that need regression coverage.
- Stale graph indexes are not evidence. Refresh if allowed; otherwise report the gap and use search, coverage output, and source reads.

## Test rules

- Test behavior, not private helpers, call counts, or layout.
- Treat slow feedback as test waste. Fast tests make agents verify more often.
- Remove waits, real I/O, redundant setup, expensive collection, unbalanced parallelism, and broad default commands before reducing checks.
- Keep coverage, race, mutation, live, browser, and end-to-end modes off the hot path unless the task is about that mode.
- Mock only system boundaries: network, clock, randomness, filesystem, subprocesses, external services.
- Prefer real collaborators or in-memory fakes for internal domain code.
- Cover success, failure, edge, boundary, and regression cases that matter.
- Use coverage to find gaps; do not write low-value assertions just to raise a number.
- Delete shallow or duplicate tests once stronger public-boundary tests cover the behavior.
- Extract helpers only after repeated setup or assertions make tests harder to read.
- Follow project conventions before introducing new frameworks, helpers, or generators.

## Feedback-loop performance

For performance mode or any slow-suite work:

1. Measure the baseline command and wall time.
2. Classify the bottleneck: discovery, import/compile/transform, setup, test body, external boundary, runner config, or parallel balance.
3. Make one cluster of changes that removes waste without weakening behavior.
4. Rerun the same command and record before/after time.
5. Add or recommend a guard: durations output, per-test ceiling, slow marker, cache, or focused command.

Prefer focused deterministic checks during edits and the broader relevant suite before final output. Do not hide failures, delete edge cases, or skip important fast tests to make a number look better.

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
- duplicate scenario matrices that should be parameterized when readability stays high
- missing business, error, edge, concurrency, or permission cases
- flaky tests from time, randomness, ordering, shared state, or real external services
- slow tests that could move down a seam without losing confidence
- real sleeps, real external I/O, coverage-on-default, expensive imports, broad discovery, repeated setup, or slow transforms in the fast path
- order dependencies, leaked globals, or shared mutable resources that block safe parallelism
- dead tests that cover deleted behavior or generated glue

Prefer each language's table-driven or parameterized pattern from `references/<lang>.md` when cases share setup and assertions. Do not force consolidation when separate tests make distinct behavior clearer.

## Verification

Run the relevant project command after changes, for example `pytest -q --maxfail=1 --tb=short`. Exact commands per language live in `references/<lang>.md`.

Use coverage commands only when coverage mode or review needs them. Report skipped checks with exact reasons.

## Output

Engineer:

```text
TEST IMPROVEMENT COMPLETE
=========================
Mode: review | refactor | coverage | tdd | performance | full
Tests changed: N
Waste removed: N
Coverage: before → after | not measured
Performance: baseline → after | not measured
Status: CLEAN | NEEDS ATTENTION

Key improvements:
- path:line — change

Verification:
- <command> — pass/fail/skipped with reason
```

Reviewer or blocked:

```text
## Proposed Changes | BLOCKED

Blocker:
- <missing artifact, framework, tool, permission, or safe seam>

### Change 1: <brief description>

File: `path/to/test_file`
Action: CREATE | MODIFY | DELETE
Code: <complete test code or changed region with enough context>
Rationale: <weak, missing, brittle, slow, or duplicate test this fixes>
Verification: <command the applier should run>
```

If no test framework exists, ask before adding one. Do not claim clean without a
passing check or an explicit skipped-check reason.