#!/usr/bin/env bash
# WorktreeCreate hook: creates a managed sibling worktree.
# Non-interactive hook contract: dirty current worktrees are refused, not prompted.

set -euo pipefail

command -v jq >/dev/null 2>&1 || {
	echo "Error: worktree-create requires jq" >&2
	exit 1
}

INPUT=$(cat)
NAME=$(echo "$INPUT" | jq -r '.name // empty')
CWD=$(echo "$INPUT" | jq -r '.cwd // empty')

[ -n "$NAME" ] || {
	echo "Error: worktree name is required" >&2
	exit 1
}
[ -n "$CWD" ] || CWD="$(pwd)"

git check-ref-format --branch "$NAME" >/dev/null 2>&1 || {
	echo "Error: invalid branch name: $NAME" >&2
	exit 1
}

cd "$CWD"
REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || {
	echo "Error: not in a git repository" >&2
	exit 1
}

if [ -n "$(git -C "$REPO_ROOT" status --porcelain)" ]; then
	echo "Error: current worktree is dirty; commit, stash, or clean it before creating another worktree" >&2
	exit 1
fi

PORCELAIN=$(git -C "$REPO_ROOT" worktree list --porcelain)
MAIN_WT=$(awk '/^worktree /{sub(/^worktree /, ""); print; exit}' <<<"$PORCELAIN")
PROJECT=$(basename "$MAIN_WT")
ROOT="$(dirname "$MAIN_WT")/$PROJECT.worktrees"
SLUG=$(printf '%s' "$NAME" | tr '/' '-')
WORKTREE_PATH="$ROOT/$SLUG"

if [ -e "$WORKTREE_PATH" ]; then
	echo "Error: worktree path already exists: $WORKTREE_PATH" >&2
	exit 1
fi

if grep -Fxq "branch refs/heads/$NAME" <<<"$PORCELAIN"; then
	echo "Error: branch is already checked out in another worktree: $NAME" >&2
	exit 1
fi

DEFAULT_BRANCH=$(git -C "$REPO_ROOT" symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null | sed 's|^origin/||' || true)
[ -n "$DEFAULT_BRANCH" ] || DEFAULT_BRANCH=main

BASE_REF=HEAD
if git -C "$REPO_ROOT" rev-parse --verify --quiet "$DEFAULT_BRANCH^{commit}" >/dev/null; then
	BASE_REF=$DEFAULT_BRANCH
elif git -C "$REPO_ROOT" rev-parse --verify --quiet "origin/$DEFAULT_BRANCH^{commit}" >/dev/null; then
	BASE_REF="origin/$DEFAULT_BRANCH"
fi

mkdir -p "$ROOT"

if git -C "$REPO_ROOT" show-ref --verify --quiet "refs/heads/$NAME"; then
	git -C "$REPO_ROOT" worktree add "$WORKTREE_PATH" "$NAME" >&2
elif git -C "$REPO_ROOT" show-ref --verify --quiet "refs/remotes/origin/$NAME"; then
	git -C "$REPO_ROOT" worktree add --track -b "$NAME" "$WORKTREE_PATH" "origin/$NAME" >&2
else
	git -C "$REPO_ROOT" worktree add "$WORKTREE_PATH" -b "$NAME" "$BASE_REF" >&2
fi

# Print path to stdout for the hook contract.
echo "$WORKTREE_PATH"
