---
allowed-tools:
- Task
- TaskOutput
- TaskCreate
- TaskUpdate
- TaskList
- Read
- Grep
- Glob
- Edit
- Write
- AskUserQuestion
- Bash(make *)
- Bash(go *)
- Bash(golangci-lint *)
- Bash(pytest *)
- Bash(ruff *)
- Bash(npm *)
- Bash(bun *)
- Bash(bunx *)
argument-hint: '[diagnose|investigate] [team]'
context: fork
description: Fix code defects with a reproducible feedback loop, root-cause diagnosis,
  minimal patch, regression test, and clean verification. Use when debugging, diagnosing,
  or resolving lint/test/build failures. NOT for behavior-preserving refactors (use
  refactoring-code), test-suite cleanup without a production bug (use improving-tests),
  or code review findings without fixes (use reviewing-code).
name: fixing-code
user-invocable: true
---

# Fix and Diagnose Code

Follow the base skill. This Claude overlay only defines tool use and execution details.

Fix the requested defect or failing gate one verified issue at a time. Do not expand
to unrelated failures without asking. No guessing.

## Arguments

- `diagnose` or `investigate`: use the hard-bug workflow with hypotheses and probes.
- `team`: spawn read-only analysis agents to challenge root cause before editing.

Use `TaskCreate` and `TaskUpdate` when the fix has more than two steps:

1. Reproduce or run the failing gate.
2. Read the failing path.
3. Diagnose root cause.
4. Patch one issue.
5. Verify narrow and broad checks.
6. Clean up probes.

## Tool order

1. Run the smallest known failing command or project gate. Prefer focused tests, lint, or typecheck while editing and the broader project gate before final output.
2. Use `Read`, `Grep`, and `Glob` to inspect the exact failing path.
3. Use `AskUserQuestion` if logs, payloads, access, repro steps, environment, or instrumentation approval are missing.
4. Use `Edit` for existing files and `Write` only for new files or complete rewrites.
5. Run the narrow repro after each patch.
6. Run the relevant broader check before final output.

Do not use destructive git commands. Do not use `--no-verify`. Do not clear caches, disable rules, or skip fast tests as a routine speed fix.

## Repro commands

Prefer configured project commands. Examples:

```bash
make lint
make test
go test ./...
ruff check .
pytest -q --maxfail=1 --tb=short
bunx vitest run path/to/file.test.ts
bun test path/to/file.test.ts
npm test
```

Use only commands supported by the repo and available tools. Browser-only debugging
belongs in `browser-automation` unless a cheaper CLI/unit signal exists.

## Hard-bug mode

Before editing, write 3-5 ranked falsifiable hypotheses. Probe one at a time. If
you add temporary logs, tag them with `[DEBUG-<short-id>]` and remove them before
final output.

If `team` is set, agents analyze only. Ask for root cause, evidence, suggested fix,
priority, and confidence. Verify their claims before editing.

## Scope control

- If all checks pass and no bug is reproduced, report that and ask for a repro artifact.
- If the failing gate contains unrelated failures, fix the requested issue first and ask before expanding.
- If the only test seam is too shallow, say so; do not create fake-confidence tests.
- If a patch causes new failures, diagnose that failure before continuing.

## Output

Use `FIX COMPLETE` for applied fixes:

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
- file:line — fix

Verification:
- <command> — pass/fail/skipped with reason
```

Use `BLOCKED` or `Proposed Changes` when tools, access, permission, or user input
prevents applying the fix. Include the exact missing artifact or permission needed.

Do not claim clean without a passing check or explicit skipped-check reason.
