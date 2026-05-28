#!/usr/bin/env bash
# Remove merged or gone local branches and their clean worktrees.
# Dry-run by default. Pass --apply to execute, --force to drop ahead branches.

set -euo pipefail

APPLY=false
FORCE=false
BASE_OVERRIDE=""
PROTECTED_BRANCHES=(main master trunk develop dev)

usage() {
	cat <<'EOF'
Usage: cleanup-git.sh [--apply] [--force] [--base <ref>]

Dry-run by default. Removes clean worktrees and local branches whose branch is
merged into the detected base branch or whose upstream is gone.
EOF
}

while [ "$#" -gt 0 ]; do
	case "$1" in
	--apply)
		APPLY=true
		shift
		;;
	--force)
		FORCE=true
		shift
		;;
	--base)
		shift
		[ "$#" -gt 0 ] || {
			echo "Error: --base requires a ref" >&2
			exit 2
		}
		BASE_OVERRIDE=$1
		shift
		;;
	--base=*)
		BASE_OVERRIDE=${1#--base=}
		shift
		;;
	-h | --help)
		usage
		exit 0
		;;
	*)
		echo "Error: unknown argument: $1" >&2
		usage >&2
		exit 2
		;;
	esac
done

cd "$(git rev-parse --show-toplevel)"
git fetch --all --prune --quiet || true

has_ref() {
	git rev-parse --verify --quiet "$1" >/dev/null
}

base_name_for_ref() {
	local ref=$1 remote stripped
	case "$ref" in
	refs/heads/*)
		printf '%s\n' "${ref#refs/heads/}"
		return 0
		;;
	refs/remotes/*)
		stripped=${ref#refs/remotes/}
		for remote in $(git remote); do
			case "$stripped" in
			"$remote"/*)
				printf '%s\n' "${stripped#"$remote/"}"
				return 0
				;;
			esac
		done
		;;
	esac
	for remote in $(git remote); do
		case "$ref" in
		"$remote"/*)
			printf '%s\n' "${ref#"$remote/"}"
			return 0
			;;
		esac
	done
	printf '%s\n' "$ref"
}

detect_base() {
	local remote head branch candidate

	for remote in $(git remote); do
		head=$(git symbolic-ref --quiet --short "refs/remotes/$remote/HEAD" 2>/dev/null || true)
		[ -n "$head" ] || continue
		branch=${head#"$remote/"}
		if has_ref "refs/heads/$branch"; then
			printf '%s\t%s\n' "$branch" "$branch"
		else
			printf '%s\t%s\n' "$head" "$branch"
		fi
		return 0
	done

	for candidate in "${PROTECTED_BRANCHES[@]}"; do
		if has_ref "refs/heads/$candidate"; then
			printf '%s\t%s\n' "$candidate" "$candidate"
			return 0
		fi
	done

	for remote in $(git remote); do
		for candidate in "${PROTECTED_BRANCHES[@]}"; do
			if has_ref "refs/remotes/$remote/$candidate"; then
				printf '%s\t%s\n' "$remote/$candidate" "$candidate"
				return 0
			fi
		done
	done

	return 1
}

if [ -n "$BASE_OVERRIDE" ]; then
	BASE_REF=$BASE_OVERRIDE
	BASE_NAME=$(base_name_for_ref "$BASE_REF")
else
	IFS=$'\t' read -r BASE_REF BASE_NAME < <(detect_base) || {
		echo "Error: no base branch found. Pass --base <ref>." >&2
		exit 1
	}
fi

has_ref "$BASE_REF^{commit}" || {
	echo "Error: base ref not found: $BASE_REF" >&2
	exit 1
}

CUR_BRANCH=$(git symbolic-ref --quiet --short HEAD || true)
CUR_WORKTREE=$(git rev-parse --show-toplevel)

run() {
	if $APPLY; then
		printf '+'
		printf ' %q' "$@"
		printf '\n'
		"$@"
	else
		printf 'would:'
		printf ' %q' "$@"
		printf '\n'
	fi
}

is_protected_branch() {
	local branch=$1 protected
	[ "$branch" = "$BASE_NAME" ] && return 0
	[ -n "$CUR_BRANCH" ] && [ "$branch" = "$CUR_BRANCH" ] && return 0
	for protected in "${PROTECTED_BRANCHES[@]}"; do
		[ "$branch" = "$protected" ] && return 0
	done
	return 1
}

reason_for() {
	local branch=$1 track
	track=$(git for-each-ref --format='%(upstream:track)' "refs/heads/$branch")
	if [[ "$track" == *gone* ]]; then
		echo gone
		return 0
	fi
	if git merge-base --is-ancestor "$branch" "$BASE_REF" 2>/dev/null; then
		echo merged
		return 0
	fi
	return 1
}

ahead_count() {
	git rev-list --count "$BASE_REF..$1" 2>/dev/null || echo 0
}

list_worktrees() {
	git worktree list --porcelain | awk '
		/^worktree / { path=substr($0, 10) }
		/^branch / { branch=$2; sub(/^refs\/heads\//, "", branch); print path "\t" branch }
		/^detached/ { print path "\tDETACHED" }
		/^bare/ { print path "\tBARE" }
	'
}

branch_in_worktree() {
	local branch=$1
	grep -Fxq "$branch" <<<"$WORKTREE_BRANCHES"
}

delete_branch() {
	local branch=$1 ahead=$2
	if [ "$ahead" -gt 0 ]; then
		run git branch -D "$branch"
		return
	fi
	if ! $APPLY; then
		run git branch -d "$branch"
		return
	fi
	printf '+ git branch -d %q\n' "$branch"
	git branch -d "$branch" 2>/dev/null || {
		echo "  -d refused; branch is safe relative to $BASE_REF, deleting with -D."
		run git branch -D "$branch"
	}
}

echo "base branch: $BASE_REF"
echo "== worktrees =="
list_worktrees | while IFS=$'\t' read -r path branch; do
	[ -n "$path" ] || continue
	[ "$path" = "$CUR_WORKTREE" ] && continue
	case "$branch" in
	DETACHED | BARE)
		echo "  skip $path ($branch)"
		continue
		;;
	esac
	if is_protected_branch "$branch"; then
		echo "  skip $path ($branch, protected)"
		continue
	fi
	if [ -n "$(git -C "$path" status --porcelain 2>/dev/null)" ]; then
		echo "  KEEP $path ($branch, dirty)"
		continue
	fi
	reason=$(reason_for "$branch") || true
	if [ -z "$reason" ]; then
		echo "  skip $path ($branch, active)"
		continue
	fi
	ahead=$(ahead_count "$branch")
	if [ "$ahead" -gt 0 ] && ! $FORCE; then
		echo "  KEEP $path ($branch, $reason, $ahead ahead — use --force)"
		continue
	fi
	ahead_suffix=""
	[ "$ahead" -gt 0 ] && ahead_suffix=", $ahead ahead"
	echo "  remove $path ($branch, $reason$ahead_suffix)"
	run git worktree remove "$path"
done

echo "== branches =="
WORKTREE_BRANCHES=$(list_worktrees | awk -F '\t' '$2 != "DETACHED" && $2 != "BARE" { print $2 }')
git for-each-ref --format='%(refname:short)' refs/heads/ | while read -r branch; do
	if is_protected_branch "$branch"; then
		echo "  skip $branch (protected)"
		continue
	fi
	if branch_in_worktree "$branch"; then
		echo "  skip $branch (in worktree)"
		continue
	fi
	reason=$(reason_for "$branch") || true
	if [ -z "$reason" ]; then
		echo "  skip $branch (active)"
		continue
	fi
	ahead=$(ahead_count "$branch")
	if [ "$ahead" -gt 0 ] && ! $FORCE; then
		echo "  KEEP $branch ($reason, $ahead ahead — use --force)"
		continue
	fi
	ahead_suffix=""
	[ "$ahead" -gt 0 ] && ahead_suffix=", $ahead ahead"
	echo "  delete $branch ($reason$ahead_suffix)"
	delete_branch "$branch" "$ahead"
done

$APPLY || echo "(dry-run — pass --apply)"
