---
description: Fix code defects with a reproducible feedback loop, root-cause diagnosis,
  minimal patch, regression test, and clean verification. Use when debugging, diagnosing,
  or resolving lint/test/build failures. NOT for behavior-preserving refactors (use
  refactoring-code), test-suite cleanup without a production bug (use improving-tests),
  or code review findings without fixes (use reviewing-code).
name: fixing-code
---

# Fix and Diagnose Code

Fix the requested defect or failing gate, one verified root cause at a time.
Use the matching `writing-<lang>` skill for toolchain commands.

Without write access, return proposed changes (file, change, reason) instead of
applying them.

## Hard rules

- No fix without a reproducible pass/fail signal. If you cannot reproduce, ask for the missing artifact (logs, payload, trace, repro steps, environment) instead of patching on a guess.
- No destructive git (hard reset, clean, force push, checkout over local changes) and no `--no-verify`.
- Never disable assertions, skip fast tests, lower lint severity, clear caches, or ignore files to make a check pass or run faster.
- Fix the requested failure first; ask before expanding to unrelated failures.

## Outcome

- **Repro**: the fastest reliable failing signal, best a failing test at the behavior seam; otherwise a script, replayed payload, or small harness around the real path. Iterate on the narrowest command; keep coverage, race, browser, and end-to-end modes off the loop unless they are the failing signal.
- **Root cause**: traced from the failing boundary to the first bad state or contract mismatch, with evidence (`file:line`, symptom, tool). For intermittent or unclear bugs, rank 3–5 falsifiable hypotheses and test them one at a time.
- **Patch**: the smallest change to the root cause, without adjacent cleanup. If it causes a new failure, diagnose that before touching anything else.
- **Regression test** at the seam where the user saw the bug. If only a shallow seam exists, say so rather than adding a fake-confidence helper test.
- **Cleanup**: temporary probes, tagged `[DEBUG-<id>]` while in use, are removed or promoted to real tests.
- If a code-graph tool (GitNexus, codegraph) is installed and fresh, use it to find callers or impact before changing widely used code.

Done when the original repro passes, the regression test passes (or the missing
seam is reported), and the relevant build/test/lint checks pass on what you
changed, or you name each check that did not run and why.

## Report

Root cause with evidence, changes (`path:line — fix`), and each check with
pass, fail, or skipped and why. If blocked, name the missing artifact, access,
or approval.

## Platform additions

No target-specific additions.
