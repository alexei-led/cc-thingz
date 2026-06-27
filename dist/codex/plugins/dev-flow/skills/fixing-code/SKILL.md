---
description: Fix code defects with a reproducible feedback loop, root-cause diagnosis,
  minimal patch, regression test, and clean verification. Use when debugging, diagnosing,
  or resolving lint/test/build failures. NOT for behavior-preserving refactors (use
  refactoring-code), test-suite cleanup without a production bug (use improving-tests),
  or code review findings without fixes (use reviewing-code).
name: fixing-code
---

# Fix and Diagnose Code

Fix the requested defect or failing gate one verified issue at a time. Do not
patch from guesses. Do not expand to unrelated failures without asking.

Never use destructive git commands such as hard reset, clean, force push, or
checkout-overwrites as a fix.

## Role-gated action

Detect capability from tools:

- Write-capable role: reproduce, diagnose, patch, test, and clean up.
- Read-only role: diagnose from files and supplied output, then emit the fix in the Proposed Changes contract. Apply nothing; run nothing.
- Missing key tool or permission: stop with Blocked and ask for the exact artifact, access, or approval needed.

Use an interactive question tool when available for missing logs, payloads,
repro steps, environment details, access, or permission for temporary instrumentation.

## Route elsewhere

Do not use this for:

- pure refactors with unchanged behavior → `refactoring-code`
- test-only improvement or coverage work → `improving-tests`
- review-only findings → `reviewing-code`
- broad architecture redesign → architecture skills
- browser-only UI investigation without a cheaper signal → `browser-automation`

## Reproduce first

For lint/build/test failures, run the fastest reliable failing signal first.
Prefer a focused test, package, or file command while editing; use `make lint`,
`make test`, or the broader project gate before final output. Use configured
language tools from the nearest project root.

For reported bugs, build the fastest reliable pass/fail signal:

1. Existing failing test or new regression test at the behavior seam.
2. CLI, HTTP, or browser script with fixture input.
3. Replay captured payload, log, trace, or production-like case.
4. Small harness around the real code path.
5. Property, fuzz, race, or bisect harness when supported and safe.

If no repro is possible, stop and ask for the missing artifact. Do not proceed to
a speculative fix.

## Fast feedback gates

Tests, lint, typecheck, format, vet, and build commands are feedback loops. Every
second is paid on each agent iteration.

- Use the narrowest reliable command while editing: one test, package, file,
  workspace, or changed-file lint when supported.
- Run the broader relevant gate before final output.
- Keep coverage, race, mutation, browser, end-to-end, live-service, and deep
  static-analysis modes off the hot path unless they are the failing signal.
- Preserve caches and incremental state. Do not clear caches as a routine fix.
- If a gate is unexpectedly slow, measure enough to name the bottleneck and either
  fix it in scope or report it as performance debt.
- Never disable assertions, skip important fast tests, lower lint severity, or
  ignore files only to make a command faster.

## Diagnose with evidence

Record each issue as `file:line`, exact symptom, reporting tool, and priority.
Trace from the failing boundary toward the first bad state, contract mismatch, or
missing side effect.

For hard bugs, write 3-5 ranked falsifiable hypotheses:

```text
If <cause> is true, then <probe/change> will make <specific symptom> change in <specific way>.
```

Use graph tools only when available and when they reduce search space:

- GitNexus: query the error text or symptom; use context for suspect symbols; use impact before changing widely called code; use detect-changes after a fix to see affected flows.
- codegraph: check freshness first; if fresh, inspect callers, callees, references, and blast radius.
- Stale graph indexes are not evidence. Refresh if allowed; otherwise report the gap and use search, source reads, LSP, and tests.

## Patch narrowly

For each issue:

1. Read the exact code path.
2. Change the smallest root cause, not adjacent style or structure.
3. Add or update a regression test when a real seam exists.
4. Run the narrow repro.
5. Run broader lint/test before moving to another issue.

For test or lint fixes, prefer targeted fast commands in the edit loop. Keep
expensive reporting commands for coverage-specific work or final gate parity, not
every patch attempt.

Do not write helper-level tests that miss the user-visible bug path. If the only
available seam is too shallow, report the risk.

If a fix causes new failures, diagnose that failure before touching the next issue.

## Cleanup and verify

Before done:

- Original repro no longer fails.
- Regression test passes, or the missing seam is reported.
- Full relevant validation passes, or skipped checks have exact reasons.
- Temporary logs, probes, harnesses, and debug flags are removed or promoted to real tests.
- New failures are diagnosed before any second patch.

## Output

Engineer:

```text
FIX COMPLETE
============
Mode: standard | diagnose | team | diagnose+team
Issues found: X
Fixed: Y
Remaining: Z
Status: CLEAN | NEEDS ATTENTION

Root cause:
- <verified cause and evidence>

Changes:
- path:line — fix

Verification:
- <command> — pass/fail/skipped with reason
```

Reviewer or blocked:

```text
## Proposed Changes | BLOCKED

Root cause:
- <verified cause and evidence, or unknown because blocked>

Blocker:
- <missing artifact, access, tool, or permission>

### Change 1: <brief description>

File: `path/to/file`
Action: CREATE | MODIFY | DELETE
Code: <complete code block or changed region with enough context>
Rationale: <why this fixes the root cause>
```

Do not claim clean without a clean check or an explicit skipped-check reason.
