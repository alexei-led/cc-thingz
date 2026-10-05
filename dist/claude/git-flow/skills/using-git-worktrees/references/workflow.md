# Worktree Edge Cases

Cases the scripts preserve or require scoped user consent for.

- Path exists: pick another branch name, or remove the leftover directory after the user confirms. Remove only paths under `<project>.worktrees/`.
- Branch checked out in another worktree: work there, or pick another branch. If that worktree's directory is gone, `git worktree prune` clears the stale registration.
- Base ref not found: fetch or pass `--base <ref>`.
- Setup refused (no lockfile, conflicting lockfiles or manager): run the project's documented install command, and ask if none exists.
- Cleanup without `gh`: the script can still prove ancestry or patch-equivalent squash. If proof fails, show the unique commits and `git -C <worktree> status --short --untracked-files=all --ignored`, then ask once for consent to remove that exact target. After consent and a state recheck, run `scripts/cleanup-worktree.sh --force <branch>` yourself.
- Refused because the branch has commits past the merged PR head, or the PR head is not local: `git fetch` first; if still refused, show `git log <pr-head>..<branch>` and use `--force` only when the user says those commits are throwaway.
- Dirty worktree: include untracked and ignored files in the loss warning. Keep it during safe cleanup; use scoped `--force` only after the user says those files are throwaway. Recheck the tip and files before executing.
- `git branch -d` refuses after a squash or rebase merge: that is expected; use `-D` once the PR is confirmed merged.
- The shell was inside the removed worktree: `cd` to the main worktree before running further commands.
