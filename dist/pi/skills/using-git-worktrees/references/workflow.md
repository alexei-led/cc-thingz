# Worktree Edge Cases

Cases the scripts refuse or leave to you.

- Path exists: pick another branch name, or remove the leftover directory after the user confirms. Remove only paths under `<project>.worktrees/`.
- Branch checked out in another worktree: work there, or pick another branch. If that worktree's directory is gone, `git worktree prune` clears the stale registration.
- Base ref not found: fetch or pass `--base <ref>`.
- Setup refused (no lockfile, conflicting lockfiles or manager): run the project's documented install command, and ask if none exists.
- Cleanup when `gh` is missing or cannot see the PR: ask the user to confirm the merge and check `git status` in the worktree, since `--force` also discards dirty files; then run `scripts/cleanup-worktree.sh --force <branch>`.
- `git branch -d` refuses after a squash or rebase merge: that is expected; use `-D` once the PR is confirmed merged.
- The shell was inside the removed worktree: `cd` to the main worktree before running further commands.
