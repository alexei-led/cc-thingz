---
{"allowed-tools":["Read","AskUserQuestion","Bash(git status *)","Bash(git branch *)","Bash(git worktree *)","Bash(git rev-parse *)","Bash(git symbolic-ref *)","Bash(git fetch *)","Bash(mkdir *)","Bash(rmdir *)","Bash(scripts/setup-worktree.sh *)","Bash(scripts/cleanup-worktree.sh *)","Bash(git switch *)","Bash(git log *)","Bash(git -C * status *)"],"context":"fork","description":"Creates and removes isolated git worktrees for parallel development. Use when starting feature work needing isolation, working on multiple branches simultaneously, or removing one specific worktree and its branch after its PR merges. NOT for simple branch switching, sweeping multiple stale worktrees or merged branches at once (use cleanup-git), or git hook/config setup (use configuring-git-hygiene).","name":"using-git-worktrees","user-invocable":true}
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

A cleanup request authorizes removal of a clean, verified merged worktree and its branch without another confirmation. The script fetches first and verifies Git ancestry, a merged PR bound to the repository/base/head, or an equivalent squash patch without `gh`. It preserves new commits and uncommitted files, including ignored files. For an exception, show the exact target, full tip OID, commits and files at risk, then ask once. After consent, recheck the tip and files and run `--force <branch>` yourself; never require the user to copy and run the command. Main, protected, and locked worktrees remain guarded even with force. For bulk or stale cleanup and command-local hook consent, use cleanup-git. Leave `git pull` out of cleanup; update the integration worktree separately only when clean and requested.

For cases the scripts refuse or don't cover, read [workflow.md](references/workflow.md).

## Output

```text
WORKTREE READY | WORKTREE REMOVED | BLOCKED
Branch: <branch>
Path: <project>.worktrees/<slug>
Next: cd <path>, or the script's refusal reason
```

Report cleanup as done only after verifying the worktree and branch are gone. Name the merge proof or the explicitly approved exception.
