---
description: Creates isolated git worktrees for parallel development. Use when starting
  feature work needing isolation or working on multiple branches simultaneously. Not
  for simple branch switching or basic git operations.
name: using-git-worktrees
---

# Git Worktrees

## Core Principle

Main repo stays on main/master — never edit directly. Every branch gets its own worktree. All worktrees for a project live under one per-project root directory, `<project>.worktrees/`, a sibling of the main repo. Delete the worktree and its branch after the PR merges.

Think of a worktree as a **disposable branch folder**, not a long-lived parallel environment.

**Exception:** Trivial one-liner commits on a solo project can go directly on main to avoid ceremony overhead.

## Workflow

Check repo state before creating a worktree. Any worktree workflow description must name this dirty-state check before `git worktree add`:

```bash
git status --short
git branch --show-current
git worktree list
```

If the current worktree is dirty, ask whether to commit, stash, or create the new worktree anyway before proceeding. Confirm before running cleanup commands that remove worktrees or delete branches.

The per-project root is derived from the main worktree, so create and clean up correctly even when invoked from inside another worktree:

```bash
# main worktree is always the first entry of `git worktree list --porcelain`
main_wt=$(git worktree list --porcelain | awk '/^worktree /{print $2; exit}')
project=$(basename "$main_wt")
root="$(dirname "$main_wt")/$project.worktrees"
```

```bash
# 1. Create worktree for new work (slug = branch with / → -)
mkdir -p "$root"
git worktree add "$root/fix-cron" -b fix-cron

# 2. Work there (open your editor or coding agent in that folder)
cd "$root/fix-cron"

# 3. After PR merges — confirm, then clean up from the main worktree
scripts/cleanup-worktree.sh fix-cron
```

Both steps are scripted: `scripts/setup-worktree.sh <branch> [base]` and `scripts/cleanup-worktree.sh [branch]`.

## Directory Layout

All worktrees for a project live under one root, `<project>.worktrees/`, a sibling of the main repo (never nested inside it):

```
~/projects/
├── myproject/                    # main worktree — always on main, always clean
└── myproject.worktrees/          # per-project worktree root
    ├── fix-cron/                 # worktree for fix-cron branch
    ├── feature-auth/             # worktree for feature/auth branch
    └── bugfix-123/               # worktree for bugfix/issue-123 branch
```

Why a sibling root: one tidy place per project, no .gitignore pollution, clean git status, independent build artifacts. The root is removed automatically once its last worktree is cleaned up.

## Naming Convention

Worktree dir is the branch slug only — slashes become dashes. No project prefix; the `<project>.worktrees/` root already scopes it.

- `fix-cron` — `myproject.worktrees/fix-cron`
- `feature/auth` — `myproject.worktrees/feature-auth`
- `bugfix/issue-123` — `myproject.worktrees/bugfix-issue-123`

## When to Suggest Worktrees

- User wants to start a new feature, fix, or experiment
- User is about to edit code on main/master
- User wants to try multiple approaches to the same problem
- User has uncommitted changes and wants to start something else

## Cleanup on PR Merge

When a PR merges, remove the worktree and delete its branch. State clearly what is being removed and why before running anything destructive.

Squash and rebase merges rewrite the commit, so `git branch -d` reports the branch as "not fully merged" even though the PR is merged. The source of truth is the PR state, not local ancestry — do not conflate them.

Use `scripts/cleanup-worktree.sh [branch]`. It is strict by default: unless `gh` confirms the PR is MERGED it changes nothing and exits with a single clear message. Pass `--force` to proceed anyway — when `gh` is not installed (you confirm the merge) or to abandon an unmerged branch on purpose; `--force` also force-removes a dirty worktree and force-deletes the branch. It defaults to the current worktree's branch, refuses to remove the main worktree, `cd`s out of the worktree before removing it, falls back to `git branch -D` for the squash/rebase case, runs `git fetch --prune`, and prunes the empty root. It does not run `git pull` — pull main yourself afterward only once you have confirmed main is checked out and clean. WORKFLOW.md has the manual command sequence for when the script is unavailable.

## Failure handling

- Worktree path already exists: pick a different branch/slug; never force-overwrite.
- Branch already exists remotely: use `git worktree add "$root/<slug>" <branch>` (no `-b`) to check it out.
- Dirty main repo when user wants a new worktree: ask to commit, stash, or proceed anyway — do not silently stash.
- `git worktree remove` fails with "is dirty": confirm with user before running `git worktree remove --force`.
- `git branch -d` says "not fully merged" after a squash/rebase PR merge: confirm the PR is MERGED, then use `git branch -D` — this is expected, not data loss.
- Invoked from inside the worktree being removed: `cd` to the main worktree first, or the shell ends up in a deleted directory.

## Output

```text
WORKTREE READY
==============
Action: CREATE | CLEANUP
Branch: <branch>
Path: <project>.worktrees/<slug>
Status: DONE | BLOCKED

Next:
- cd into the worktree path and open the editor there, or
- pull main yourself after a confirmed cleanup
```

For cleanup, only report DONE when the PR is confirmed MERGED (or `--force` was used deliberately); otherwise status is BLOCKED with the single reason the script reported.

## References

- [WORKFLOW.md](references/WORKFLOW.md) - Detailed steps, project setup, cleanup, common mistakes
- [scripts/](scripts/) - setup-worktree.sh and cleanup-worktree.sh
