#!/usr/bin/env bash
# WorktreeRemove hook: removes only clean managed worktrees.
# It is not PR-merge cleanup; unmerged branches are kept for cleanup-git.

set -euo pipefail

command -v jq >/dev/null 2>&1 || {
	echo "Error: worktree-remove requires jq" >&2
	exit 1
}

INPUT=$(cat)
WORKTREE_PATH=$(echo "$INPUT" | jq -r '.worktree_path // empty')

[ -n "$WORKTREE_PATH" ] || exit 0
[ -d "$WORKTREE_PATH" ] || exit 0

WT=$(git -C "$WORKTREE_PATH" rev-parse --show-toplevel 2>/dev/null) || exit 0
PORCELAIN=$(git -C "$WT" worktree list --porcelain)
MAIN_WT=$(awk '/^worktree /{sub(/^worktree /, ""); print; exit}' <<<"$PORCELAIN")
PROJECT=$(basename "$MAIN_WT")
MANAGED_ROOT="$(dirname "$MAIN_WT")/$PROJECT.worktrees"

if ! awk -v wt="$WT" '/^worktree /{path=substr($0, 10); if (path == wt) found=1} END{exit found ? 0 : 1}' <<<"$PORCELAIN"; then
	echo "Refusing to remove path that is not a registered git worktree: $WT" >&2
	exit 1
fi

case "$WT" in
"$MANAGED_ROOT"/*) ;;
*)
	echo "Refusing to remove unmanaged worktree path: $WT" >&2
	exit 1
	;;
esac

if [ "$WT" = "$MAIN_WT" ]; then
	echo "Refusing to remove main worktree: $WT" >&2
	exit 1
fi

if [ -n "$(git -C "$WT" status --porcelain)" ]; then
	echo "Refusing to remove dirty worktree: $WT" >&2
	exit 1
fi

BRANCH=$(git -C "$WT" symbolic-ref --quiet --short HEAD 2>/dev/null || true)
case "$BRANCH" in
main | master | trunk | develop | dev)
	echo "Refusing to delete protected branch: $BRANCH" >&2
	exit 1
	;;
esac

cd "$MAIN_WT"
git worktree remove "$WT"

if [ -n "$BRANCH" ]; then
	if git branch -d "$BRANCH" >/dev/null 2>&1; then
		echo "Deleted merged branch: $BRANCH" >&2
	else
		echo "Kept branch '$BRANCH' because it is not fully merged; use cleanup-git after PR merge" >&2
	fi
fi

ROOT=$(dirname "$WT")
rmdir "$ROOT" 2>/dev/null || true
