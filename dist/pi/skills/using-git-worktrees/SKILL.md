---
description: Creates isolated git worktrees for parallel development. Use when starting
  feature work needing isolation or working on multiple branches simultaneously. NOT
  for simple branch switching, bulk branch cleanup (use cleanup-git), or git hook/config
  setup (use configuring-git-hygiene).
name: using-git-worktrees
---

<!-- Pi platform guidance -->
<!-- Use Pi tool names exactly: read, bash, edit, write, ask_user_question, structured_output, todo, subagent, wait, web_search, web_answer, web_research. -->
<!-- Use subagent for delegated work. Use wait to block on async subagent runs only when no independent work remains. -->
<!-- Use ctx7 or npx ctx7@latest through bash when Context7 documentation lookup is required. -->

# Git Worktrees

Use one sibling worktree root per project: `<project>.worktrees/<branch-slug>`. Keep the main worktree clean on the integration branch by default. Trivial solo one-liners may stay in the main worktree when a worktree would add pointless ceremony.

Treat a worktree as a disposable branch folder. Remove it and its branch after the PR merges.

## Scope

Use this skill when:

- starting a feature, fix, or experiment that should not disturb current work
- working on multiple branches at once
- trying competing approaches
- the current worktree has uncommitted changes and the user wants to start something else

Do not use this skill for:

- simple branch switching with no parallel work
- bulk branch or stale worktree cleanup — use `cleanup-git`
- git hook, Gitleaks, `.gitignore`, or config setup — use `configuring-git-hygiene`

## Create Workflow

Check state before any `git worktree add`:

```bash
git status --short
git branch --show-current
git worktree list
```

If the current worktree is dirty, ask whether to commit, stash, or proceed anyway. Do not stash silently.

Use the helper when available:

```bash
scripts/setup-worktree.sh <branch> [--base <ref>]
```

The helper creates `<project>.worktrees/<branch-slug>` from the main worktree root, handles existing local/remote branches, refuses path conflicts, and refuses dirty state unless `--allow-dirty` is passed after user approval.

Manual fallback lives in [workflow.md](references/workflow.md).

## Naming

- Root: sibling `<project>.worktrees/` directory.
- Directory: branch slug only; replace `/` with `-`.
- Examples: `fix-cron`, `feature-auth`, `bugfix-issue-123`.

## Cleanup Workflow

For one named worktree after PR merge:

```bash
scripts/cleanup-worktree.sh [branch]
```

The helper refuses unless `gh` confirms the PR is `MERGED`. Pass `--force` only after the user confirms the merge without `gh` or confirms the branch should be abandoned.

For bulk cleanup, stale worktrees, gone upstreams, or merged local branches, use `cleanup-git`.

Do not run `git pull` as part of cleanup. Pull the integration branch only after confirming the main worktree is checked out and clean.

## Failure Handling

- Worktree path exists: pick a different branch/slug; never overwrite.
- Branch already exists remotely: check it out without `-b` or use the helper.
- Dirty current worktree: ask to commit, stash, or continue with explicit approval.
- `git worktree remove` fails because the worktree is dirty: confirm before `--force`.
- `git branch -d` fails after squash/rebase PR merge: confirm the PR is `MERGED`, then use `-D`.
- Invoked from inside the worktree being removed: change to the main worktree before removing it.

## Output

```text
WORKTREE READY
==============
Action: CREATE | CLEANUP
Branch: <branch>
Path: <project>.worktrees/<slug>
Status: DONE | BLOCKED

Next:
- cd <path> and open the editor there, or
- pull the integration branch yourself after confirmed cleanup
```

For cleanup, report `DONE` only when the PR is confirmed `MERGED` or `--force` was used deliberately. Otherwise report `BLOCKED` with the script's reason.

## References

- [workflow.md](references/workflow.md) — manual fallback and edge cases
- [scripts/](scripts/) — `setup-worktree.sh` and `cleanup-worktree.sh`
