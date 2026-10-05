#!/usr/bin/env bash
# Remove one merged worktree and its branch; --force attests scoped user consent.
set -euo pipefail

FORCE=0
BRANCH=""
usage() {
	cat <<'EOF'
Usage: cleanup-worktree.sh [--force] [branch-name]

Removes a clean worktree after a verified PR merge, Git ancestry, or equivalent
squash patch. --force requires explicit user consent to discard this branch's
commits and uncommitted files. Main, protected, and locked worktrees stay.
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
		exit 2
		;;
	*)
		[ -z "$BRANCH" ] || {
			echo "Error: branch already set" >&2
			exit 2
		}
		BRANCH=$1
		shift
		;;
	esac
done

porcelain=$(git worktree list --porcelain) || exit 1
MAIN_WT=$(awk '/^worktree /{print substr($0,10); exit}' <<<"$porcelain")
BRANCH=${BRANCH:-$(git symbolic-ref --quiet --short HEAD || true)}
[ -n "$BRANCH" ] || {
	echo "Error: detached HEAD — pass a branch"
	exit 1
}
WT=$(awk -v b="refs/heads/$BRANCH" '/^worktree /{p=substr($0,10)} $0=="branch "b{print p; exit}' <<<"$porcelain")
[ -n "$WT" ] || {
	echo "Error: no worktree for '$BRANCH'"
	exit 1
}
[ "$WT" != "$MAIN_WT" ] || {
	echo "Error: refusing MAIN worktree"
	exit 1
}

cd "$MAIN_WT"
git fetch --all --prune --quiet || {
	echo "Error: fetch failed; refusing stale merge proof"
	exit 1
}
BASE=""
for remote in origin $(git remote | grep -vx origin); do
	BASE=$(git symbolic-ref --quiet --short "refs/remotes/$remote/HEAD" || true)
	[ -z "$BASE" ] || break
done
if [ -z "$BASE" ]; then
	for remote in origin $(git remote | grep -vx origin); do
		for name in main master trunk develop dev; do
			if git rev-parse --verify --quiet "$remote/$name^{commit}" >/dev/null; then
				BASE="$remote/$name"
				break 2
			fi
		done
	done
fi
if [ -z "$BASE" ]; then
	for ref in main master trunk develop dev; do
		if git rev-parse --verify --quiet "$ref^{commit}" >/dev/null; then
			BASE=$ref
			break
		fi
	done
fi
BASE_REMOTE=origin
BASE_NAME=$BASE
for remote in $(git remote); do
	case "$BASE" in
	"$remote/"*)
		BASE_REMOTE=$remote
		BASE_NAME=${BASE#"$remote/"}
		break
		;;
	esac
done
case "$BRANCH" in
main | master | trunk | develop | dev)
	echo "Error: protected branch '$BRANCH'"
	exit 1
	;;
esac
[ "$BRANCH" != "$BASE_NAME" ] || {
	echo "Error: protected base branch"
	exit 1
}
if awk -v target="$WT" '/^worktree /{p=substr($0,10)} /^locked/{if(p==target) found=1} END{exit !found}' <<<"$porcelain"; then
	echo "Refusing: locked worktree '$WT'"
	exit 1
fi

TIP=$(git rev-parse --verify "refs/heads/$BRANCH")
STATE=""
PR_HEAD=""
PR_BASE=""
PR_MERGE=""
repo_args=()
remote_url=$(git remote get-url "$BASE_REMOTE" 2>/dev/null || true)
[ -z "$remote_url" ] || repo_args=(--repo "$remote_url")
if command -v gh >/dev/null 2>&1; then
	info=$(gh pr view "$BRANCH" "${repo_args[@]}" --json state,headRefOid,baseRefName,mergeCommit --template '{{printf "%s\t%s\t%s\t%s" .state .headRefOid .baseRefName .mergeCommit.oid}}' 2>/dev/null || true)
	IFS=$'\t' read -r STATE PR_HEAD PR_BASE PR_MERGE <<<"$info"
fi

MERGED=0
if [ -n "$BASE" ]; then
	if git merge-base --is-ancestor "$TIP" "$BASE" 2>/dev/null; then
		MERGED=1
	elif [ "$STATE" = MERGED ] && [ "$PR_BASE" = "$BASE_NAME" ] &&
		[[ "$PR_MERGE" =~ ^([0-9a-f]{40}|[0-9a-f]{64})$ ]] &&
		git merge-base --is-ancestor "$PR_MERGE" "$BASE" 2>/dev/null; then
		if [[ "$PR_HEAD" =~ ^([0-9a-f]{40}|[0-9a-f]{64})$ ]] &&
			git merge-base --is-ancestor "$TIP" "$PR_HEAD" 2>/dev/null; then MERGED=1; fi
	else
		ancestor=$(git merge-base "$BASE" "$TIP" 2>/dev/null || true)
		probe=$(git -c user.name=cleanup -c user.email=cleanup@localhost commit-tree "$TIP^{tree}" -p "$ancestor" -m cleanup-squash-probe 2>/dev/null || true)
		cherry=$(git cherry "$BASE" "$probe" 2>/dev/null || true)
		[[ "$cherry" != "- "* ]] || MERGED=1
	fi
fi
if [ "$MERGED" != 1 ] && [ "$FORCE" != 1 ]; then
	echo "Refusing: merge not proven, PR head unavailable, or commits beyond merged PR. Try git fetch."
	echo "Nothing was changed. Explain the commits/files at risk and ask for consent before --force."
	exit 1
fi
status=$(git -C "$WT" status --porcelain --untracked-files=all --ignored) || {
	echo "Refusing: status unknown"
	exit 1
}
if [ -n "$status" ] && [ "$FORCE" != 1 ]; then
	echo "Refusing: dirty worktree (including untracked/ignored files)."
	printf '%s\n' "$status"
	echo "Ask for consent to discard these files before --force."
	exit 1
fi

echo "Removing worktree: $WT"
approval=()
if [ "$FORCE" = 1 ]; then
	approval=(-c "cc-thingz.cleanupApproved=$TIP")
	git "${approval[@]}" worktree remove --force "$WT"
else
	git worktree remove "$WT"
fi
echo "Deleting branch: $BRANCH"
git branch -d "$BRANCH" 2>/dev/null || git "${approval[@]}" branch -D "$BRANCH"
ROOT=$(dirname "$WT")
rmdir "$ROOT" 2>/dev/null || true
echo "Done. Worktree removed and branch handled for '$BRANCH'."
echo "Main worktree: $MAIN_WT (pull only when clean and on the integration branch)."
