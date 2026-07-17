---
{"description":"Create normal git commits with logical grouping. Use when committing, saving changes, creating commits, or grouping work into commits. NOT for amending, rebasing, force-pushing, or rewriting history.","name":"committing-code"}
---
<!-- Pi platform guidance -->
<!-- Use installed Pi tool names exactly. Installed extensions may add toolsets such as Task*, Monitor*, and Loop*; use the visible tool names exactly and do not translate them to Claude syntax. -->
<!-- Prefer Task* over `todo` when task-tracking tools are available; `todo` is the cc-thingz fallback. Prefer MonitorCreate for long-running or background commands and LoopCreate for scheduled or event-driven follow-up instead of Bash sleep/poll loops. -->
<!-- Use subagent for delegated work. Use wait to block on async subagent runs only when no independent work remains. -->
<!-- Use ctx7 or npx ctx7@latest through bash when Context7 documentation lookup is required. -->


# Commit Changes

Scope: inspect changes, group them, and create normal commits only. Do not rewrite history, amend existing commits, force-push, or stage secrets. Ground the proposal in git status, diff, and recent log output.

## Step 1: Gather State

Use `scripts/commit-state.sh gather` if present; otherwise gather status, diff stat, and recent commits.

The helper is read-only. Treat helper output as a hint, not proof.

If grouping is unclear, inspect the full diff.

- If no changes: say "Nothing to commit" and stop.
- If not a git repository: report "Not a git repository" and stop.
- If detached HEAD or rebase/merge is interrupted: report the git state verbatim and stop.

## Step 2: Choose Fast Path or Split Path

Use the fast path when all are true:

- few changed files
- small diff stat
- one coherent purpose from gathered output
- no suspicious paths
- no obvious mix of code, docs, tests, CI, or config for different purposes

Then propose one commit. No deep exploration. No invented split.

If mixed or unclear, inspect the full diff and group by purpose: feature, fix, refactor, docs, config. Use diff evidence, not filenames alone.

Match commit style from recent history.

## Step 3: Present Proposed Commits

```text
Proposed commits:

1. feat: add user validation
   - src/validate.ts
   - src/validate_test.ts

2. docs: update README
   - README.md
```

If the user rejects the grouping, ask for revised grouping and do not proceed until approved.

## Step 4: Execute

Never stage likely secrets: `.env`, keys, certificates, credentials, passwords, tokens, or files that appear to contain secrets. Flag them to the user if detected in changes. This check does not replace secret-scanning tools.

Pause for user approval before any `git add` or `git commit`. For one focused commit, one approval gate is enough. For multiple commits, pause before each commit.

If a pre-commit hook rejects, report the hook error verbatim. Do not retry with `--no-verify`.

## Conditional References

- [conventions.md](references/conventions.md) — read when the repo has no commit history to match, or when the user requests Conventional Commits format: type prefixes, scope rules, breaking-change notation, subject-line style.

## Step 5: Summary

Show final status, created commits, and remaining uncommitted files.