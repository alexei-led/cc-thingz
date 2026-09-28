---
description: Creates isolated git worktrees for parallel development. Use when starting
  feature work needing isolation or working on multiple branches simultaneously. NOT
  for simple branch switching, bulk branch cleanup (use cleanup-git), or git hook/config
  setup (use configuring-git-hygiene).
name: using-git-worktrees
---

# Git Worktrees

A worktree gives parallel work its own folder and branch while the main worktree stays clean on the integration branch. Each project gets one sibling root, `<project>.worktrees/`, with one directory per branch named by its slug (`/` → `-`, so `feature/auth` → `feature-auth`). Remove the worktree and branch after the PR merges.

A plain branch switch with no parallel work needs no worktree: check `git status --short`, then `git switch <branch>`. Trivial solo one-liners may also stay in the main worktree.

## Create

Check `git status --short` and `git worktree list` first. Leave uncommitted changes where they are and never stash them silently; pass `--allow-dirty` only when the user has authorized isolating new work while keeping them.

```bash
scripts/setup-worktree.sh <branch> [--base <ref>] [--allow-dirty] [--setup] [--test]
```

The script runs `git worktree add` from the main worktree root. It checks out an existing local or `origin` branch instead of recreating it, and refuses an existing path, a branch checked out in another worktree, or a dirty tree without `--allow-dirty`. It reports base divergence from local refs without fetching.

- `--setup` does a frozen install with the declared package manager and lockfile (uv for Python). Conflicting lockfiles or manager declarations stop it. A setup failure exits non-zero but still prints the path.
- `--test` runs the detected baseline tests. Failures only warn.
- A skipped setup or test is not a pass.

## Clean up one worktree

```bash
scripts/cleanup-worktree.sh [branch]
```

It removes the worktree and deletes the branch only when `gh` confirms the PR is `MERGED`. It also refuses when the branch has commits past the merged PR head. Pass `--force` only after the user confirms the merge without `gh`, confirms those extra commits are throwaway, or abandons the branch; `--force` can remove a dirty worktree and force-delete the branch. For bulk or stale cleanup, use cleanup-git. Leave `git pull` out of cleanup; the user pulls the main worktree once it is clean on the integration branch.

For cases the scripts refuse or don't cover, read [workflow.md](references/workflow.md).

## Output

```text
WORKTREE READY | WORKTREE REMOVED | BLOCKED
Branch: <branch>
Path: <project>.worktrees/<slug>
Next: cd <path>, or the script's refusal reason
```

Report a cleanup as done only when the PR is confirmed `MERGED` or `--force` was deliberate.
