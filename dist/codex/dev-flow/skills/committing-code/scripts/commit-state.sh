#!/usr/bin/env bash
# Read-only git change summary for the committing-code skill.
# Helps the model avoid rebuilding the same inspection shell every time.

set -euo pipefail

usage() {
	cat <<'EOF'
Usage: commit-state.sh [gather|full-diff|paths|suspicious]

Commands:
  gather      Print repo state, changed paths, diff stats, suspicious paths, recent commits
  full-diff   Print git diff against HEAD
  paths       Print changed and untracked paths
  suspicious  Print only suspicious paths
EOF
}

ensure_git_repo() {
	git rev-parse --show-toplevel >/dev/null 2>&1 || {
		echo "Not a git repository" >&2
		exit 2
	}
}

repo_root() {
	git rev-parse --show-toplevel
}

branch_name() {
	git symbolic-ref --quiet --short HEAD 2>/dev/null || echo "DETACHED"
}

rebase_or_merge_state() {
	local git_dir
	git_dir=$(git rev-parse --git-dir)
	if [ -f "$git_dir/MERGE_HEAD" ]; then
		echo "merge in progress"
		return
	fi
	if [ -d "$git_dir/rebase-merge" ] || [ -d "$git_dir/rebase-apply" ]; then
		echo "rebase in progress"
		return
	fi
	if [ "$(branch_name)" = "DETACHED" ]; then
		echo "detached HEAD"
		return
	fi
	if [ -f "$git_dir/CHERRY_PICK_HEAD" ]; then
		echo "cherry-pick in progress"
		return
	fi
	if [ -f "$git_dir/REVERT_HEAD" ]; then
		echo "revert in progress"
		return
	fi
	if [ -f "$git_dir/BISECT_LOG" ]; then
		echo "bisect in progress"
		return
	fi
	echo "clean"
}

has_head() {
	git rev-parse --verify --quiet HEAD >/dev/null
}

changed_paths() {
	{
		if has_head; then
			git diff --name-only HEAD
		else
			git diff --cached --name-only
		fi
		git ls-files --others --exclude-standard
	} | awk 'NF' | sort -u
}

suspicious_path_names() {
	changed_paths | awk '
		BEGIN { IGNORECASE = 1 }
		/(^|\/)[.]env($|[.])|\.pem$|\.key$|\.p12$|credentials|secret|password|token/ { print }
	'
}

suspicious_content_paths() {
	local path
	changed_paths | while IFS= read -r path; do
		[ -f "$path" ] || continue
		if grep -Eiq -- '(api[_-]?key|access[_-]?token|auth[_-]?token|secret|password|private[ -]?key)' "$path"; then
			printf '%s\n' "$path"
		fi
	done | sort -u
}

suspicious_paths() {
	{
		suspicious_path_names
		suspicious_content_paths
	} | sort -u
}

status_short() {
	git status --short
}

shortstat() {
	if has_head; then
		git diff --shortstat HEAD || true
	else
		git diff --cached --shortstat || true
	fi
}

diff_stat() {
	if has_head; then
		git diff --stat HEAD
	else
		git diff --cached --stat
	fi
}

recent_log() {
	git log --oneline -8 2>/dev/null || true
}

gather() {
	ensure_git_repo
	local root branch state file_count suspicious_count
	root=$(repo_root)
	branch=$(branch_name)
	state=$(rebase_or_merge_state)
	file_count=$(changed_paths | awk 'NF{n++} END{print n+0}')
	# shellcheck disable=SC2016
	suspicious_count=$(suspicious_paths | awk 'NF{n++} END{print n+0}')

	printf 'REPO_ROOT\n%s\n\n' "$root"
	printf 'BRANCH\n%s\n\n' "$branch"
	printf 'REPO_STATE\n%s\n\n' "$state"
	printf 'CHANGED_FILE_COUNT\n%s\n\n' "$file_count"
	printf 'STATUS_SHORT\n'
	status_short || true
	printf '\nDIFF_SHORTSTAT\n'
	shortstat
	printf '\nDIFF_STAT\n'
	diff_stat || true
	printf '\nCHANGED_PATHS\n'
	changed_paths || true
	printf '\nSUSPICIOUS_PATH_COUNT\n%s\n\n' "$suspicious_count"
	printf 'SUSPICIOUS_PATHS\n'
	suspicious_paths || true
	printf '\nRECENT_COMMITS\n'
	recent_log || true
}

cmd=${1:-gather}
case "$cmd" in
gather)
	gather
	;;
full-diff)
	ensure_git_repo
	if has_head; then
		git diff HEAD
	else
		git diff --cached
	fi
	;;
paths)
	ensure_git_repo
	changed_paths
	;;
suspicious)
	ensure_git_repo
	suspicious_paths
	;;
-h | --help | help)
	usage
	;;
*)
	echo "Error: unknown command: $cmd" >&2
	usage >&2
	exit 2
	;;
esac
