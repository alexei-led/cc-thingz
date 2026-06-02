#!/usr/bin/env bash
# Remove a worktree and delete its branch after its PR has merged.

set -euo pipefail

FORCE=0
BRANCH=""

usage() {
	cat <<'EOF'
Usage: cleanup-worktree.sh [--force] [branch-name]

Default is strict: if gh cannot confirm the PR is MERGED, nothing is touched.
Use --force only after confirming the merge yourself or deciding to abandon the
branch. --force may remove a dirty worktree and force-delete the branch.
EOF
}

while [ "$#" -gt 0 ]; do
	case "$1" in
	--force)
		FORCE=1
		shift
		;;
	-h | --help)
		usage
		exit 0
		;;
	-*)
		echo "Error: unknown option: $1" >&2
		usage >&2
		exit 2
		;;
	*)
		[ -z "$BRANCH" ] || {
			echo "Error: branch name already set: $BRANCH" >&2
			exit 2
		}
		BRANCH=$1
		shift
		;;
	esac
done

porcelain=$(git worktree list --porcelain 2>/dev/null) || {
	echo "Error: Not in a git repository"
	exit 1
}

MAIN_WT=$(awk '/^worktree /{print $2; exit}' <<<"$porcelain")

if [ -z "$BRANCH" ]; then
	BRANCH=$(git rev-parse --abbrev-ref HEAD)
	[ "$BRANCH" = "HEAD" ] && {
		echo "Error: detached HEAD — pass a branch name explicitly"
		exit 1
	}
fi

WT=$(awk -v b="refs/heads/$BRANCH" '
	/^worktree /{p=$2} $0=="branch "b{print p; exit}' <<<"$porcelain")

if [ -z "$WT" ]; then
	echo "Error: no worktree checked out on branch '$BRANCH'"
	git worktree list
	exit 1
fi
if [ "$WT" = "$MAIN_WT" ]; then
	echo "Error: '$BRANCH' is checked out in the MAIN worktree ($MAIN_WT) — refusing to remove it"
	exit 1
fi

GH=0
STATE=""
if command -v gh >/dev/null 2>&1; then
	GH=1
	STATE=$(gh pr view "$BRANCH" --json state --jq .state 2>/dev/null || echo "")
fi
[ "$GH" = 1 ] && pr_desc="PR for '$BRANCH' is ${STATE:-not found}" || pr_desc="gh not installed, PR state for '$BRANCH' unknown"

if [ "$STATE" = MERGED ]; then
	echo "PR for '$BRANCH' is MERGED — cleaning up."
elif [ "$FORCE" = 1 ]; then
	echo "$pr_desc — proceeding due to --force. This may force-remove dirty files and force-delete the branch."
else
	echo "Refusing: $pr_desc."
	echo "Nothing was changed. Re-run with --force once the PR has merged or to abandon the branch."
	exit 1
fi

cd "$MAIN_WT"

echo "Removing worktree: $WT"
if [ "$FORCE" = 1 ]; then
	git worktree remove --force "$WT"
else
	git worktree remove "$WT" || {
		echo "Error: 'git worktree remove' failed (likely dirty). Re-run with --force after confirming."
		exit 1
	}
fi

echo "Deleting branch: $BRANCH"
git branch -d "$BRANCH" 2>/dev/null || {
	echo "  -d refused after confirmed merge/force — deleting with -D."
	git branch -D "$BRANCH"
}

git fetch --prune --quiet || true

ROOT=$(dirname "$WT")
rmdir "$ROOT" 2>/dev/null && echo "Removed empty worktree root: $ROOT" || true

echo ""
echo "Done. Worktree removed and branch handled for '$BRANCH'."
echo "Main worktree: $MAIN_WT (pull it yourself once it is on the integration branch and clean)."
