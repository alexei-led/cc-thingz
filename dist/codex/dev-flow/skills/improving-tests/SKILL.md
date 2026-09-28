---
{"description":"Improve test design, speed, and coverage with behavior-focused tests, useful seams, characterization tests, TDD, and test refactoring. Use when improving tests, optimizing slow suites, adding coverage, refactoring brittle tests, removing test waste, or working test-first. NOT for fixing production bugs (use fixing-code), production-code refactors (use refactoring-code), or reviewing non-test code quality (use reviewing-code).","name":"improving-tests"}
---
<!-- Platform guidance for Codex -->
<!-- Use this platform's installed tool names exactly; do not translate capability references into Claude Code tool syntax. -->
<!-- When this skill references shell execution, file reads, or search, use the platform's native shell, read, and search tools. -->
<!-- If a referenced helper command or optional tool is unavailable, report the gap and continue with the platform's built-in tools. -->


# Test Improvement

Make tests catch real behavior regressions without blocking safe changes. Suite
latency is a quality attribute; coverage is a signal, not the goal.

Without write access, return proposed changes (file, change, reason) instead of
applying them.

Read the reference for each language in scope; it covers test patterns and
suite speed. Use the matching `writing-<lang>` skill for toolchain commands.

- C#: `references/csharp.md`
- Go: `references/go.md`
- Java/Kotlin: `references/java-kotlin.md`
- Python: `references/python.md`
- Rust: `references/rust.md`
- TypeScript/JavaScript: `references/typescript.md`
- Browser, Playwright, HTMX: `references/web.md`

## Modes

If the mode is missing, ask which one:

- `review`: find weak, duplicate, brittle, missing, slow, or flaky tests.
- `refactor`: simplify tests without changing covered behavior.
- `coverage`: add tests for uncovered business behavior and error paths.
- `tdd`: one red-green-refactor slice at a time.
- `performance`: cut suite latency without weakening behavior.
- `full`: all of the above.

## Rules

- Ask before adding a test framework, runner plugin, or tool. Learn the framework, helpers, and conventions from nearby tests and follow them first.
- Change production code only inside an approved TDD slice. If no safe behavior seam exists, stop and report what production change would create one.
- Test through the contract users or adjacent modules rely on: public module, API, CLI, component, or service. Use an integration seam when behavior depends on real wiring (database, filesystem, HTTP, serialization, config); a unit seam when behavior is pure and cheap.
- Mock only system boundaries (network, clock, randomness, filesystem, subprocesses, external services). Prefer real collaborators or in-memory fakes for domain code.
- Assert behavior, not private helpers, call counts, or layout. Business-critical arguments get exact matches.
- Parameterize cases that share setup and assertions; keep separate tests when that reads clearer.
- Delete shallow or duplicate tests once stronger boundary tests cover the behavior.
- Characterization tests before risky changes to legacy code capture current visible behavior, quirks included, at the public boundary.
- TDD: each slice has one test that failed for the expected reason before the smallest passing code, and refactoring happens only while green. No bulk suites for imagined behavior.
- If a code-graph tool (GitNexus, codegraph) is installed and fresh, use it to find affected flows and high fan-in code that needs regression coverage.

## Speed

Performance work records the same command's wall time before and after, names
the bottleneck (discovery, import or compile, setup, test body, external
boundary, runner config, or parallel balance), and leaves a guard against
regression (durations output, per-test ceiling, slow marker, or focused command).

- Remove waste before removing checks: real sleeps, real external I/O, repeated setup, expensive imports, broad discovery, coverage-on-default.
- Keep coverage, race, mutation, browser, live, and end-to-end modes off the default loop; run them in their own tier.
- Parallelism needs isolated state: per-test or per-worker ports, temp dirs, databases, and filenames. Treat parallel-only failures as isolation bugs.
- Never make a number look better by hiding failures, deleting edge cases, or skipping fast tests.

Done when the relevant build/test/lint checks pass on what you changed, or you
name each check that did not run and why.

## Report

Mode, tests changed, key changes (`path:line — change`), coverage and timing
before → after when measured, and each check with pass, fail, or skipped and why.

## Platform additions

No target-specific additions.
