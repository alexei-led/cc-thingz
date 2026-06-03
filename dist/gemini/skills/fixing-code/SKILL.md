---
description: Fix code defects with a reproducible feedback loop, root-cause diagnosis,
  minimal patch, regression test, and clean verification. Use when debugging, diagnosing,
  or resolving lint/test/build failures. NOT for behavior-preserving refactors (use
  refactoring-code), test-suite cleanup without a production bug (use improving-tests),
  or code review findings without fixes (use reviewing-code).
name: fixing-code
---

# Fix and Diagnose Code

Fix one verified problem at a time. Do not patch from guesses. Do not use destructive
git commands such as hard reset, clean, force push, or checkout-overwrites as a fix.

## Role-gated action

Detect capability from tools:

- Write-capable role: reproduce, diagnose, patch, test, and clean up.
- Read-only role: diagnose from files and supplied output, then emit the fix in the Proposed Changes contract. Apply nothing; run nothing.

## Route elsewhere

Do not use this for:

- pure refactors with unchanged behavior → `refactoring-code`
- test-only improvement or coverage work → `improving-tests`
- review-only findings → `reviewing-code`
- broad architecture redesign → architecture skills

## Reproduce first

For lint/build/test failures, run the project gate first. Prefer `make lint` and
`make test` when present; otherwise use the configured language tools from the
nearest project root.

For reported bugs, build the fastest reliable pass/fail signal:

1. Existing failing test or new regression test at the behavior seam.
2. CLI, HTTP, or browser script with fixture input.
3. Replay captured payload, log, trace, or production-like case.
4. Small harness around the real code path.
5. Property, fuzz, race, or bisect harness for intermittent or regression bugs.

If no repro is possible, stop and ask for the missing artifact: logs, payload,
steps, environment, access, or permission to add temporary instrumentation.

## Diagnose with evidence

Record each issue as `file:line`, exact symptom, reporting tool, and priority.
For hard bugs, write 3–5 ranked falsifiable hypotheses:

```text
If <cause> is true, then <probe/change> will make <specific symptom> change in <specific way>.
```

Trace from the failing boundary toward the first bad state, contract mismatch,
or missing side effect. Use graph tools when they reduce search space:

- GitNexus: query the error text or symptom; use context for suspect symbols; use impact before changing widely called code; use detect-changes after a fix to see affected flows.
- codegraph: check status first; if fresh, use context or affected to inspect callers, callees, references, and blast radius.
- Stale graph indexes are not evidence. Refresh if allowed; otherwise report the gap and use search, LSP, tests, and source reads.

## Patch narrowly

For each issue:

1. Read the exact code path.
2. Change the smallest root cause, not adjacent style or structure.
3. Add or update a regression test when a real seam exists.
4. Run the narrow repro.
5. Run broader lint/test before moving to another issue.

Do not write helper-level tests that miss the user-visible bug path. If the only
available seam is too shallow, report the risk.

## Cleanup and verify

Before done:

- Original repro no longer fails.
- Regression test passes, or the missing seam is reported.
- Full relevant validation passes.
- Temporary logs, probes, harnesses, and debug flags are removed or promoted to real tests.
- New failures are diagnosed before any second patch.

## Output

Engineer:

```text
FIX COMPLETE
============
Issues found: X
Fixed: Y
Remaining: Z
Status: CLEAN | NEEDS ATTENTION

Root cause:
- <verified cause and evidence>

Changes:
- path:line — fix

Verification:
- <command> — pass/fail
```

Reviewer:

```text
## Proposed Changes

Root cause:
- <verified cause and evidence>

### Change 1: <brief description>

File: `path/to/file`
Action: CREATE | MODIFY | DELETE

Code:
<complete code block or changed region with enough context>

Rationale: <why this fixes the root cause>
```

If unresolved, state the blocker and exact artifact or access needed. Do not claim clean without a clean check or an explicit skipped-check reason.
