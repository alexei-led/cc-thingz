---
allowed-tools:
- Bash(git status *)
- Bash(git diff *)
- Bash(git log *)
- Bash(git show *)
- Bash(git branch *)
- Bash(scripts/commit-state.sh *)
context: fork
description: Smart git commits with logical grouping. Use when user says "commit",
  "commit changes", "save changes", "create commit", "bundle commits", "git commit",
  or wants to commit their work.
name: committing-code
user-invocable: true
---

# Smart Commit

Make focused commits. Fast path for small coherent changes. Split only when the diff shows separate purposes.

Scope: only inspect changes, group them, and create normal commits. Do not rewrite history, amend existing commits, force-push, or stage secrets. Include relevant `git status`, `git diff`, and `git log` output in the proposal.

Not for squashing, rebasing, or cherry-picking — those rewrite history.

## Step 1: Gather State

Prefer the helper script:

```bash
scripts/commit-state.sh gather
```

Fallback if the script is unavailable:

```bash
git status --short
git diff --stat HEAD
git log --oneline -8
```

Run the full diff only when needed:

```bash
scripts/commit-state.sh full-diff
# fallback: git diff HEAD
```

`gather` is read-only. It shows repo state, changed paths, diff stat, suspicious paths, and recent commits.

**If no changes:** Say "Nothing to commit" → stop.
**If not a git repository:** Report "Not a git repository" → stop.
**If detached HEAD or interrupted rebase/merge:** Report the git state verbatim → stop.

## Step 2: Fast Path or Split Path

Use the fast path when all are true:

- few changed files
- small diff stat
- one coherent purpose from the gathered output
- no suspicious paths
- no obvious mix of code + docs + CI/config for different purposes

Then propose one commit. No deep exploration. No invented split.

If any check fails, or the purpose is mixed or unclear, inspect the full diff and group files logically: feature (impl + tests), fix (bug + test), refactor, docs, config. Base grouping on diff output only — do not infer purpose from filename alone.

Match commit style from recent history.

### Present proposed commits

```text
Proposed commits:

1. feat: add user validation
   - src/validate.ts
   - src/validate_test.ts

2. docs: update README
   - README.md
```

**If user rejects the grouping:** Ask for revised grouping; do not proceed until approved.

## Step 3: Execute

Never stage files matching `.env`, `*.pem`, `*.key`, `*.p12`, `*credentials*`, `*secret*`, `*password*`, or `*token*`. Flag them to the user if detected in changes.

Pause for user approval before any `git add` and `git commit`. For one focused commit, one approval gate is enough. For multiple commits, pause before each commit.

**If pre-commit hook rejects:** Report the hook error verbatim; do not retry with `--no-verify`.

## Step 4: Summary

Run final checks and show the result:

```bash
git status --short
git log --oneline -n <number-of-created-commits>
```

Summarize commits created and any remaining uncommitted files.

## Helper Script

Helper path: `scripts/commit-state.sh`

Useful commands:

```bash
scripts/commit-state.sh gather
scripts/commit-state.sh full-diff
```

Treat helper output as a hint, not proof. If the change still looks mixed, read the full diff and split it properly.
