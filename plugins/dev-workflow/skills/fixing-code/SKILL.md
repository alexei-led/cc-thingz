---
name: fixing-code
description: Fix code problems with disciplined diagnosis — run checks, build a repro for bugs, rank falsifiable hypotheses, fix one issue at a time, and verify until clean. Use when user says "fix", "debug", "diagnose", "broken", "failing", "throws", "performance regression", "make tests pass", or wants lint/test/build failures resolved.
user-invocable: true
context: fork
argument-hint: "[diagnose|investigate] [team]"
allowed-tools:
  - Task
  - TaskOutput
  - TaskCreate
  - TaskUpdate
  - TaskList
  - Bash(make *)
  - Bash(go *)
  - Bash(golangci-lint *)
  - Bash(pytest *)
  - Bash(ruff *)
  - Bash(npm *)
  - Bash(bun *)
  - Bash(bunx *)
  - mcp__plugin_claude-mem_mcp-search__search
  - mcp__plugin_claude-mem_mcp-search__get_observations
---

# Fix and Diagnose Code

Fix until clean. For hard bugs, diagnose before editing. No guessing. Confirm before any destructive command; never use `git reset --hard`, `git clean`, or force push as a fix.

**Parse `$ARGUMENTS`:**

- `diagnose` or `investigate` → hard-bug workflow: feedback loop, repro, hypotheses, probes, regression test.
- `team` → parallel analysis agents challenge root causes before fixes.

Use TaskCreate / TaskUpdate to track:

1. Run validation or build a repro
2. Analyze root causes
3. Fix one issue at a time
4. Verify after each fix
5. Final verification and cleanup

## Phase 1: Feedback Loop First

For lint/build/test failures, run validation:

```bash
make lint 2>&1 | head -150
make test 2>&1 | head -150
```

No Makefile? Detect language:

- Go: `golangci-lint run ./... 2>&1 | head -150 && go test -race ./... 2>&1 | head -150`
- Python: `ruff check . 2>&1 | head -150 && pytest --tb=short 2>&1 | head -150`
- TypeScript: `bun lint 2>&1 | head -150 && bun test 2>&1 | head -150`
- Web: `bunx eslint "**/*.js" 2>&1 | head -100 && bunx stylelint "**/*.css" 2>&1 | head -100`

If all checks pass: report `All checks pass` and stop.

For reported bugs or `diagnose`/`investigate`, build a fast, deterministic pass/fail signal before editing. Try, in order:

1. Failing unit/integration/e2e test at the right seam.
2. CLI or HTTP script with fixture input.
3. Playwright/headless browser script for UI bugs.
4. Replay captured payload/log/trace.
5. Throwaway harness around the smallest real code path.
6. Property/fuzz loop for intermittent wrong output.
7. `git bisect run` harness for regressions.
8. Human-in-the-loop script if manual steps are unavoidable.

Do not proceed to fixes until the loop reproduces the user's symptom. If no loop is possible, stop and ask for access, logs, HAR/core dump, screen recording with timestamps, or permission to add temporary instrumentation.

## Phase 2: Analyze Root Causes

Read the failing output and relevant files. If claude-mem is available, search for prior gotchas on failing files.

For straightforward check failures, catalog every distinct issue:

- file:line
- exact error/test failure
- tool that reported it
- priority: critical / important / minor

For hard bugs, generate **3–5 ranked falsifiable hypotheses** before testing any one of them:

```text
If <cause> is true, then <probe/change> will make <specific symptom> disappear or change.
```

Avoid testing only the first plausible hypothesis; that anchors the fix on guesswork.

If `team` is set, spawn relevant language QA/test/implementation agents in parallel. Agents analyze only; they must not edit. Ask them for root cause, evidence, suggested fix, priority, and confidence.

## Phase 3: Instrument Carefully

Probe one hypothesis at a time.

- Prefer debugger/REPL inspection when available.
- Otherwise add targeted logs at boundaries that distinguish hypotheses.
- Tag temporary logs with a unique prefix like `[DEBUG-a4f2]`.
- For performance regressions: measure baseline first, then bisect/profile. Do not fix from guesswork.

## Phase 4: Fix One Issue at a Time

For each issue, in priority order:

1. Read the exact code path.
2. Apply the smallest root-cause fix.
3. Add or update a regression test at the correct seam when possible.
4. Run the narrow check.
5. Run broader lint/test before moving on.

If the only available test seam is too shallow, say so. Do not write a fake-confidence test that only proves a helper works while the real bug path stays uncovered.

If a fix causes new failures, revert or adjust it before touching the next issue.

## Phase 5: Final Verification and Cleanup

Required before done:

- Original repro no longer reproduces.
- Regression test passes, or missing test seam is explicitly reported.
- Full validation passes.
- All `[DEBUG-...]` probes are removed.
- Throwaway harnesses are deleted or clearly moved into test fixtures.

Run:

```bash
make lint && make test
```

Or language equivalents.

Loop back to Phase 2 if anything still fails.

## Output

```text
FIX COMPLETE
============
Mode: standard | diagnose | team | diagnose+team
Issues found: X
Fixed: Y
Remaining: Z
Status: CLEAN | NEEDS ATTENTION

Root cause:
- <short verified cause>

Changes:
- file:line — fix

Verification:
- <command> — pass/fail
```

If unresolved, state the blocker and the exact artifact/access needed. Do not pretend clean.
