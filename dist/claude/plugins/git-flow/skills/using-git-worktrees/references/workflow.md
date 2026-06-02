# Git Worktree Workflow

## Root and Path

Derive the root from the main worktree, not the current directory. This keeps paths stable when invoked from another worktree.

```bash
main_wt=$(git worktree list --porcelain | awk '/^worktree /{print $2; exit}')
project=$(basename "$main_wt")
root="$(dirname "$main_wt")/$project.worktrees"
slug=$(printf '%s' "$BRANCH_NAME" | tr '/' '-')
path="$root/$slug"
```

Check conflicts before creation:

```bash
[ -e "$path" ] && echo "worktree path exists: $path" && exit 1
git worktree list --porcelain | grep -Fxq "branch refs/heads/$BRANCH_NAME" && echo "branch already checked out" && exit 1
```

## Create

New branch:

```bash
mkdir -p "$root"
git worktree add "$path" -b "$BRANCH_NAME" "$BASE_REF"
```

Existing local branch:

```bash
git worktree add "$path" "$BRANCH_NAME"
```

Existing remote branch:

```bash
git worktree add --track -b "$BRANCH_NAME" "$path" "origin/$BRANCH_NAME"
```

After creation, ask before running dependency setup or baseline tests. Do not install packages silently.

## Cleanup After PR Merge

Confirm what will be removed before running destructive commands. Do not remove the current shell's working directory.

```bash
branch=feature/auth
main_wt=$(git worktree list --porcelain | awk '/^worktree /{print $2; exit}')
wt=$(git worktree list --porcelain | awk -v b="refs/heads/$branch" '
  /^worktree /{p=$2} $0=="branch "b{print p; exit}')

gh pr view "$branch" --json state,mergedAt
cd "$main_wt"
git worktree remove "$wt"
git branch -d "$branch" 2>/dev/null || git branch -D "$branch"
git fetch --prune
rmdir "$(dirname "$wt")" 2>/dev/null || true
```

Use `git branch -D` only after the PR is confirmed merged or the user confirms abandonment. Squash and rebase merges often make `git branch -d` refuse even after the PR merged.

## Edge Cases

- Simple branch switch: do not create a worktree; check dirty state and use normal branch switching.
- Path exists: choose a new branch or remove the stale path after user confirmation.
- Branch checked out elsewhere: reuse that worktree or choose another branch.
- Dirty worktree: ask before force removal.
- Unmanaged path: do not remove it through this workflow.
