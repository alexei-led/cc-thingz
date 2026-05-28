---
name: cleanup-git
description: Remove merged local branches and stale git worktrees. Use when the user says "cleanup branches", "prune worktrees", "tidy git", "remove merged branches", "gone branches", or wants to clean local git state.
---

# Cleanup Git

Clean local git branches and worktrees after work has merged. Dry-run first. Destructive commands require user approval.

## Command

Run from anywhere inside a repository:

```bash
scripts/cleanup-git.sh
scripts/cleanup-git.sh --apply
scripts/cleanup-git.sh --apply --force
scripts/cleanup-git.sh --base <ref>
```

## Branch Detection

The script fetches/prunes remotes, then chooses the comparison branch:

1. Remote default branch from `refs/remotes/<remote>/HEAD`.
2. Local `main`, `master`, `trunk`, `develop`, or `dev`.
3. Remote `<remote>/{main,master,trunk,develop,dev}`.

Use `--base <ref>` only for unusual repositories.

## What It Removes

- Worktrees whose branch is merged into the detected base branch or whose upstream is gone.
- Local branches with the same criteria.

## Guards

Hard guards:

- Skip the current worktree.
- Skip the current branch.
- Skip the detected base branch and common long-lived branches: `main`, `master`, `trunk`, `develop`, `dev`.
- Keep worktrees with uncommitted changes.

Soft guard:

- Keep items with commits ahead of the base branch. `--force` overrides only this guard.

## Workflow

1. Run `scripts/cleanup-git.sh` and show the preview.
2. Surface every `KEEP` line as a human decision.
3. Ask before running `scripts/cleanup-git.sh --apply`.
4. Use `--force` only when the user confirms ahead commits are throwaway.
