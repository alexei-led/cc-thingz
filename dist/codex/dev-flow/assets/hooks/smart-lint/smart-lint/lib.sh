#!/usr/bin/env bash
# Shared utilities for smart-lint modules: colors, logging, error collection, formatters.

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
YELLOW='\033[0;33m'
NC='\033[0m'
CLAUDE_HOOKS_DEBUG="${CLAUDE_HOOKS_DEBUG:-0}"
PROJECT_TYPE="${PROJECT_TYPE:-unknown}"
SMART_LINT_DIFF_FALLBACK_LIMIT="${SMART_LINT_DIFF_FALLBACK_LIMIT:-5}"
SMART_LINT_COMPACT_LINES=80
SMART_LINT_OUTPUT_BYTES=1048576
# Per-command cap so one slow/cold tool (pyright's first node spin-up,
# golangci-lint's first cache build, …) can't eat the whole hook budget. A
# value that isn't a plain positive integer (empty, non-numeric, zero, or
# with a leading zero like "00"/"08" -- ambiguous with octal and rejected
# rather than guessed at) falls back to the default instead of turning into
# a `sleep`/no-op that defeats the cap.
SMART_LINT_CMD_TIMEOUT_SECONDS="${SMART_LINT_CMD_TIMEOUT_SECONDS:-30}"
case "$SMART_LINT_CMD_TIMEOUT_SECONDS" in
'' | 0* | *[!0-9]*) SMART_LINT_CMD_TIMEOUT_SECONDS=30 ;;
esac
# Whole-hook wall-clock budget, comfortably under hook.json's 120000ms
# harness timeout, so a loop of several run_with_timeout calls (e.g. rustfmt
# over many files) can't add up past it one call at a time. Not
# user-configurable: a value at or above the harness timeout would defeat it.
SMART_LINT_HOOK_BUDGET_SECONDS=100
HOOK_PROJECT_FALLBACK="${HOOK_PROJECT_FALLBACK:-0}"
SMART_LINT_FORMAT_RAN=0
SMART_LINT_LINT_RAN=0
SMART_LINT_LINT_RUNS=0
SMART_LINT_UNSUPPORTED=()
SMART_LINT_STATE_NAMESPACE=cc-thingz/hooks-v2
SMART_LINT_TIMEOUT_COUNT=0
SMART_LINT_INCOMPLETE_COUNT=0
export -n HOOK_INPUT_JSON
HOOK_INPUT_JSON="${HOOK_INPUT_JSON:-}"
HOOK_EDITED_FILES_LOADED=0
HOOK_EDITED_FILES=()

log_debug() { [[ "$CLAUDE_HOOKS_DEBUG" == "1" ]] && echo -e "${CYAN}[DEBUG]${NC} $*" >&2; }
log_info() { echo -e "${BLUE}[INFO]${NC} $*" >&2; }
report_incomplete() {
	SMART_LINT_INCOMPLETE_COUNT=$((SMART_LINT_INCOMPLETE_COUNT + 1))
	log_info "incomplete: $*"
}
command_exists() { command -v "$1" &>/dev/null; }
mark_format_ran() { SMART_LINT_FORMAT_RAN=1; }
mark_lint_ran() {
	SMART_LINT_LINT_RAN=1
	SMART_LINT_LINT_RUNS=$((SMART_LINT_LINT_RUNS + 1))
}
project_fallback_enabled() { [[ "$HOOK_PROJECT_FALLBACK" == "1" && ! -f ".nohooks-project" ]]; }

find_local_node_bin() {
	local name="$1" dir="$PWD"
	while [[ -n "$dir" && "$dir" != "/" ]]; do
		if [[ -x "$dir/node_modules/.bin/$name" ]]; then
			printf '%s\n' "$dir/node_modules/.bin/$name"
			return 0
		fi
		dir=$(dirname "$dir")
	done
	return 1
}

resolve_node_tool() {
	local name="$1" bin
	bin=$(find_local_node_bin "$name" || true)
	if [[ -n "$bin" ]]; then
		printf '%s\n' "$bin"
		return 0
	fi
	if command_exists "$name"; then
		printf '%s\n' "$name"
		return 0
	fi
	return 1
}

find_upward_file() {
	local name="$1" dir="$PWD"
	while [[ -n "$dir" && "$dir" != "/" ]]; do
		if [[ -f "$dir/$name" ]]; then
			printf '%s\n' "$dir/$name"
			return 0
		fi
		dir=$(dirname "$dir")
	done
	return 1
}

package_json_mentions_node_tool() {
	local tool="$1" package_json="$2"
	[[ -f "$package_json" ]] || return 1
	case "$tool" in
	biome) grep -qiE '(@biomejs/biome|"biome"[[:space:]]*:|(^|[[:space:]/;&])biome([[:space:]@;&]|$))' "$package_json" 2>/dev/null ;;
	oxfmt) grep -qiE '("oxfmt"[[:space:]]*:|(^|[[:space:]/;&])oxfmt([[:space:]@;&]|$))' "$package_json" 2>/dev/null ;;
	oxlint) grep -qiE '(@oxc-project/oxlint|"oxlint"[[:space:]]*:|(^|[[:space:]/;&])oxlint([[:space:]@;&]|$))' "$package_json" 2>/dev/null ;;
	eslint) grep -qiE '("eslint"[[:space:]]*:|(^|[[:space:]/;&])eslint([[:space:]@;&]|$))' "$package_json" 2>/dev/null ;;
	prettier) grep -qiE '("prettier"[[:space:]]*:|(^|[[:space:]/;&])prettier([[:space:]@;&]|$))' "$package_json" 2>/dev/null ;;
	*) return 1 ;;
	esac
}

# Project declarations win; callers separately resolve installed binaries so an
# absent declared tool can fall back without adding per-tool environment flags.
node_tool_is_adopted() {
	local tool="$1" package_json
	case "$tool" in
	biome | oxfmt | oxlint | eslint | prettier) ;;
	*) return 1 ;;
	esac
	if node_tool_configured "$tool"; then return 0; fi
	package_json=$(find_upward_file package.json || true)
	[[ -n "$package_json" ]] || return 1
	package_json_mentions_node_tool "$tool" "$package_json"
}

node_tool_configured() {
	local tool="$1" dir="$PWD" marker
	while [[ -n "$dir" && "$dir" != "/" ]]; do
		case "$tool" in
		biome)
			for marker in biome.json biome.jsonc; do
				[[ -f "$dir/$marker" ]] && return 0
			done
			;;
		oxfmt)
			for marker in .oxfmtrc .oxfmtrc.json .oxfmtrc.jsonc .oxfmtrc.js .oxfmtrc.mjs .oxfmtrc.cjs .oxfmtrc.ts .oxfmtrc.mts .oxfmtrc.cts; do
				[[ -f "$dir/$marker" ]] && return 0
			done
			;;
		oxlint)
			for marker in .oxlintrc .oxlintrc.json .oxlintrc.jsonc oxlint.config.json oxlint.config.jsonc oxlint.config.js oxlint.config.mjs oxlint.config.cjs oxlint.config.ts oxlint.config.mts oxlint.config.cts; do
				[[ -f "$dir/$marker" ]] && return 0
			done
			;;
		eslint)
			for marker in .eslintrc .eslintrc.json .eslintrc.json5 .eslintrc.yaml .eslintrc.yml .eslintrc.js .eslintrc.mjs .eslintrc.cjs eslint.config.js eslint.config.mjs eslint.config.cjs eslint.config.ts; do
				[[ -f "$dir/$marker" ]] && return 0
			done
			;;
		prettier)
			for marker in .prettierrc .prettierrc.json .prettierrc.json5 .prettierrc.yaml .prettierrc.yml .prettierrc.js .prettierrc.mjs .prettierrc.cjs prettier.config.js prettier.config.mjs prettier.config.cjs prettier.config.ts; do
				[[ -f "$dir/$marker" ]] && return 0
			done
			;;
		esac
		dir=$(dirname "$dir")
	done
	return 1
}

package_json_has_script() {
	local script="$1"
	[[ -f package.json ]] || return 1
	command_exists python3 || return 1
	python3 -c '
import json
import sys
from pathlib import Path

script = sys.argv[1]
try:
    data = json.loads(Path("package.json").read_text())
except (OSError, json.JSONDecodeError):
    sys.exit(1)
scripts = data.get("scripts", {})
if isinstance(scripts, dict) and isinstance(scripts.get(script), str):
    sys.exit(0)
sys.exit(1)
' "$script" 2>/dev/null
}

package_script_runner() {
	[[ -f package.json ]] || return 1
	if [[ -f yarn.lock ]] && command_exists yarn; then
		printf 'yarn|yarn\n'
		return 0
	fi
	if { [[ -f bun.lock ]] || [[ -f bun.lockb ]]; } && command_exists bun; then
		printf 'bun|bun\n'
		return 0
	fi
	if command_exists npm; then
		printf 'npm|npm\n'
		return 0
	fi
	if command_exists yarn; then
		printf 'yarn|yarn\n'
		return 0
	fi
	if command_exists bun; then
		printf 'bun|bun\n'
		return 0
	fi
	return 1
}

run_package_script_compact() {
	local script="$1" runner kind bin
	package_json_has_script "$script" || return 1
	runner=$(package_script_runner || true)
	[[ -n "$runner" ]] || return 1
	kind=${runner%%|*}
	bin=${runner#*|}
	case "$kind" in
	yarn) run_command_compact "yarn $script" "$bin" run "$script" || true ;;
	bun) run_command_compact "bun $script" "$bin" run "$script" || true ;;
	npm) run_command_compact "npm $script" "$bin" run --silent "$script" || true ;;
	*) return 1 ;;
	esac
	return 0
}

python_project_mentions_tool() {
	local name="$1" file
	if [[ "$name" == "ruff" && (-f ruff.toml || -f .ruff.toml) ]]; then return 0; fi
	if [[ -f pyproject.toml ]] && command_exists python3; then
		python3 -c '
import re
import sys
from pathlib import Path

try:
    import tomllib
except ImportError:
    sys.exit(1)

tool = sys.argv[1].lower().replace("_", "-")
try:
    data = tomllib.loads(Path("pyproject.toml").read_text())
except OSError:
    sys.exit(1)
except tomllib.TOMLDecodeError:
    sys.exit(1)


def dep_name(value):
    if not isinstance(value, str):
        return ""
    return re.split(r"[<>=!~; \[]", value.strip(), maxsplit=1)[0].lower().replace("_", "-")


def walk_deps(value):
    if isinstance(value, list):
        for item in value:
            yield dep_name(item)
    elif isinstance(value, dict):
        for nested in value.values():
            yield from walk_deps(nested)

configured = data.get("tool", {})
if isinstance(configured, dict) and tool in configured:
    sys.exit(0)
project = data.get("project", {})
if tool in set(walk_deps(project.get("dependencies", []))):
    sys.exit(0)
if tool in set(walk_deps(project.get("optional-dependencies", {}))):
    sys.exit(0)
if tool in set(walk_deps(data.get("dependency-groups", {}))):
    sys.exit(0)
sys.exit(1)
' "$name" 2>/dev/null && return 0
	fi
	if [[ -f uv.lock ]] && grep -qiE "^name = \"${name}\"$" uv.lock 2>/dev/null; then
		return 0
	fi
	for file in requirements.txt requirements-dev.txt; do
		[[ -f "$file" ]] || continue
		if grep -qiE "^[[:space:]]*${name}([<>=!~ ;\[]|$)" "$file" 2>/dev/null; then
			return 0
		fi
	done
	return 1
}

init_hook_input() {
	if [[ -z "$HOOK_INPUT_JSON" && ! -t 0 ]]; then
		HOOK_INPUT_JSON=$(cat 2>/dev/null || true)
	fi
	SMART_LINT_PI_RUNTIME=0
	SMART_LINT_TARGET_STATUS=0
	SMART_LINT_SESSION_ID=default
	if command_exists python3; then
		local hook_cwd file
		{
			# shellcheck disable=SC2034 # main.sh reserves stdout for the Pi decision.
			if ! IFS= read -r -d '' SMART_LINT_PI_RUNTIME; then
				report_incomplete "Cannot read hook input metadata; checks skipped"
				return 1
			fi
			IFS= read -r -d '' hook_cwd
			IFS= read -r -d '' SMART_LINT_SESSION_ID
			IFS= read -r -d '' SMART_LINT_TARGET_STATUS
			while IFS= read -r -d '' file; do HOOK_EDITED_FILES+=("$file"); done
		} < <(python3 -I -S "$(dirname "${BASH_SOURCE[0]}")/normalize-input.py" <<<"$HOOK_INPUT_JSON")
		if [[ -n "$hook_cwd" ]] && ! cd "$hook_cwd"; then
			report_incomplete "Cannot enter hook project cwd"
			return 1
		fi
		HOOK_EDITED_FILES_LOADED=1
	else
		report_incomplete "Cannot read hook input metadata: python3 unavailable"
		return 1
	fi
	return 0
}

hook_edit_target_outside_project() {
	[[ "${SMART_LINT_TARGET_STATUS:-0}" == "1" ]]
}

hook_edit_target_unavailable() {
	[[ "${SMART_LINT_TARGET_STATUS:-0}" == "2" ]]
}

declare -a ERRORS=()
add_error() {
	ERRORS+=("${RED}❌ $1${NC}\n$2")
}

print_summary_and_exit() {
	local unsupported
	for unsupported in "${SMART_LINT_UNSUPPORTED[@]}"; do report_incomplete "$unsupported"; done
	if [[ "${#ERRORS[@]}" -gt 0 ]]; then
		echo -e "${RED}❌ ${#ERRORS[@]} check problem(s) (advisory):${NC}" >&2
		for err in "${ERRORS[@]}"; do echo -e "$err" >&2; done
	fi
	if [[ "$SMART_LINT_TIMEOUT_COUNT" -gt 0 || "$SMART_LINT_INCOMPLETE_COUNT" -gt 0 ]]; then
		echo -e "${YELLOW}⚠️ Style checks incomplete: ${SMART_LINT_TIMEOUT_COUNT} timed out, ${SMART_LINT_INCOMPLETE_COUNT} unavailable or failed${NC}" >&2
	elif [[ "${#ERRORS[@]}" -eq 0 ]]; then
		if [[ "$SMART_LINT_LINT_RAN" -eq 0 ]]; then
			log_info "unsupported: no lint checks completed"
		else
			echo -e "${PROJECT_TYPE} project ${GREEN}✅ Style OK${NC}" >&2
		fi
	fi
	exit 0
}

# Run selected files from their owning package, leaving state tracking at the
# original hook root. Node tools may still inherit workspace config/binaries.
lint_project_groups() {
	local manifest="$1"
	shift
	local original_files=("${HOOK_EDITED_FILES[@]}") files=() roots=() owners=() group=()
	local file dir root old_pwd="$PWD" i before
	while IFS= read -r file; do files+=("$file"); done < <(get_changed_files "$@")
	[[ "${#files[@]}" -gt 0 ]] || return 0
	for file in "${files[@]}"; do
		dir=$(dirname "$file")
		root=.
		while [[ "$dir" != "." && "$dir" != "/" ]]; do
			if [[ -f "$dir/$manifest" ]]; then
				root="$dir"
				break
			fi
			dir=$(dirname "$dir")
		done
		roots+=("$root")
		owners+=("$root")
	done
	while IFS= read -r root; do
		group=()
		for ((i = 0; i < ${#files[@]}; i++)); do
			[[ "${owners[i]}" == "$root" ]] || continue
			file=${files[i]}
			[[ "$root" == "." ]] || file=${file#"$root/"}
			group+=("$file")
		done
		if ! cd "$old_pwd/$root"; then
			report_incomplete "Cannot enter project $root"
			continue
		fi
		HOOK_EDITED_FILES=("${group[@]}")
		before="$SMART_LINT_LINT_RUNS"
		case "$manifest" in
		pyproject.toml) lint_python ;;
		go.mod) lint_go ;;
		package.json) lint_typescript ;;
		esac
		if [[ "$SMART_LINT_LINT_RUNS" -eq "$before" ]]; then
			SMART_LINT_UNSUPPORTED+=("No focused lint check completed in $root ($manifest)")
		fi
		cd "$old_pwd" || {
			report_incomplete "Cannot restore hook cwd"
			return 0
		}
	done < <(printf '%s\n' "${roots[@]}" | sort -u)
	HOOK_EDITED_FILES=("${original_files[@]}")
}

lint_scope_has_input() {
	local type="$1" file extensions=()
	case "$type" in
	csharp) extensions=(.cs .csproj .sln .props .targets) ;;
	rust) extensions=(.rs Cargo.toml Cargo.lock rust-toolchain rust-toolchain.toml) ;;
	jvm) extensions=(.java .kt .kts pom.xml build.gradle settings.gradle gradle.properties) ;;
	yaml | github_actions) extensions=(.yml .yaml) ;;
	json) extensions=(.json) ;;
	shell) extensions=(.sh .bash) ;;
	terraform) extensions=(.tf .tfvars) ;;
	markdown) extensions=(.md) ;;
	*) return 1 ;;
	esac
	while IFS= read -r file; do
		if [[ "$type" == github_actions && "$file" != .github/workflows/* ]]; then continue; fi
		[[ -z "$file" ]] || return 0
	done < <(get_changed_files "${extensions[@]}")
	return 1
}

_extract_hook_files_jq() {
	command_exists jq || return 0
	jq -r '(.tool_input // .) | .. | objects | (.file_path? // .path? // .filename? // empty)' <<<"$HOOK_INPUT_JSON" 2>/dev/null | while IFS= read -r file; do
		[[ -n "$file" && -f "$file" ]] && printf '%s\n' "$file"
	done
}

_hook_session_id() {
	printf '%s\n' "${SMART_LINT_SESSION_ID:-default}"
}

_hook_state_path() {
	git rev-parse --git-dir >/dev/null 2>&1 || return 1
	local session_id safe_session_id scope
	scope=$(git rev-parse --show-prefix 2>/dev/null) || return 1
	session_id=$(_hook_session_id)
	safe_session_id=$(printf '%s' "$session_id" | tr -c 'A-Za-z0-9_.-' '_')
	git rev-parse --git-path "$SMART_LINT_STATE_NAMESPACE/${scope}hook-files-${safe_session_id:-default}" 2>/dev/null
}

load_hook_edited_files() {
	[[ "$HOOK_EDITED_FILES_LOADED" -eq 1 ]] && return 0
	HOOK_EDITED_FILES_LOADED=1
	HOOK_EDITED_FILES=()
	[[ -n "$HOOK_INPUT_JSON" ]] || return 0

	local file
	while IFS= read -r file; do
		[[ -n "$file" ]] && HOOK_EDITED_FILES+=("$file")
	done < <(_extract_hook_files_jq | sort -u)
	log_debug "Hook-scoped files: ${HOOK_EDITED_FILES[*]}"
}

record_hook_edited_files() {
	load_hook_edited_files
	[[ "${#HOOK_EDITED_FILES[@]}" -gt 0 ]] || return 0

	local state_path state_dir
	state_path=$(_hook_state_path) || return 0
	state_dir=$(dirname "$state_path")
	if ! mkdir -p "$state_dir" 2>/dev/null; then
		report_incomplete "Cannot create pending-file tracking directory"
		return 0
	fi
	# A single O_APPEND write cannot overwrite another concurrent edit event.
	# Stop normalizes/deduplicates records, so no read/merge/rename is needed.
	if ! printf '%s\0' "${HOOK_EDITED_FILES[@]}" | python3 -I -S -c '
import os
import sys
try:
    data = sys.stdin.buffer.read().replace(b"\0", b"\n")
    flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(sys.argv[1], flags, 0o600)
    try:
        if os.write(fd, data) != len(data):
            raise OSError("incomplete pending-file append")
    finally:
        os.close(fd)
except OSError as error:
    print(f"Cannot record pending files: {error}", file=sys.stderr)
    sys.exit(1)
' "$state_path"; then
		report_incomplete "Pending-file tracking failed; verification is incomplete"
	fi
}

path_is_excluded() {
	local file="$1"
	local exclude_patterns=(
		"node_modules/"
		"vendor/"
		"venv/"
		".venv/"
		"env/"
		"virtualenv/"
		"dist/"
		"build/"
		"target/"
		".tox/"
		".eggs/"
		"__pycache__/"
		".pytest_cache/"
		".mypy_cache/"
		".cargo/"
		".next/"
		".nuxt/"
		"coverage/"
	)
	local pattern
	for pattern in "${exclude_patterns[@]}"; do
		if [[ "$file" == *"$pattern"* ]]; then
			return 0
		fi
	done
	return 1
}

_matches_extension() {
	local file="$1"
	shift
	local ext base
	base=$(basename "$file")
	for ext in "$@"; do
		if [[ "$ext" == .* ]]; then
			[[ "$file" == *"$ext" ]] && return 0
		else
			[[ "$base" == "$ext" ]] && return 0
		fi
	done
	return 1
}

_diff_fallback_files() {
	if ! git rev-parse --git-dir >/dev/null 2>&1; then
		return
	fi
	{
		git diff --relative --name-only --diff-filter=ACMRTUXB --cached HEAD 2>/dev/null || true
		git diff --relative --name-only --diff-filter=ACMRTUXB 2>/dev/null || true
		git ls-files --others --exclude-standard 2>/dev/null || true
	} | sort -u | while IFS= read -r file; do
		[[ -n "$file" && -f "$file" ]] || continue
		path_is_excluded "$file" && continue
		printf '%s\n' "$file"
	done
}

get_changed_files() {
	# Usage: get_changed_files ".go" or get_changed_files ".js" ".ts" ".jsx" ".tsx"
	local extensions=("$@")
	local candidates=()
	local source="hook input"
	local file

	load_hook_edited_files
	if [[ "${#HOOK_EDITED_FILES[@]}" -gt 0 ]]; then
		candidates=("${HOOK_EDITED_FILES[@]}")
	else
		source="git diff fallback"
		while IFS= read -r file; do
			candidates+=("$file")
		done < <(_diff_fallback_files)
		if [[ "${#candidates[@]}" -gt "$SMART_LINT_DIFF_FALLBACK_LIMIT" ]]; then
			log_info "Skipping diff-wide lint fallback: ${#candidates[@]} changed files exceeds SMART_LINT_DIFF_FALLBACK_LIMIT=$SMART_LINT_DIFF_FALLBACK_LIMIT"
			return 0
		fi
	fi

	for file in "${candidates[@]}"; do
		[[ -n "$file" && -f "$file" ]] || continue
		path_is_excluded "$file" && continue
		_matches_extension "$file" "${extensions[@]}" || continue
		printf '%s\n' "$file"
	done | sort -u
	log_debug "Changed-file source: $source"
}

compact_output() {
	local max_lines="$SMART_LINT_COMPACT_LINES" max_bytes=8000
	LC_ALL=C awk -v max="$max_lines" -v budget="$max_bytes" '
		/^[[:space:]]*$/ { next }
		{
			count++
			if (count > max || used >= budget) { truncated=1; next }
			line=$0
			if (length(line) > budget-used) { line=substr(line, 1, budget-used); truncated=1 }
			print line
			used+=length(line)+1
		}
		END { if (truncated) print "... output truncated ..." }
	' <<<"$1"
}

# Runs "$@" with a wall-clock cap (min($1, time left in the hook's overall
# SMART_LINT_HOOK_BUDGET_SECONDS), so a loop over many files -- rustfmt over
# each changed file, say -- can't blow past the harness's own hook timeout
# one call at a time. Prints the command's combined output like a plain
# $(...) capture would, and exits 124 (matching GNU timeout) when it had to
# kill the command.
#
# Bash job control owns each tool process group. The bounded Python reader
# lives inside that group, so overflow and cancellation stop its descendants.
# If capture cannot run safely, skip instead of launching an unbounded tool.
run_with_timeout() (
	local secs="$1"
	shift

	local remaining=$((SMART_LINT_HOOK_BUDGET_SECONDS - SECONDS))
	if [[ "$remaining" -le 0 ]]; then
		echo "hook wall-clock budget (${SMART_LINT_HOOK_BUDGET_SECONDS}s) exhausted"
		return 124
	fi
	[[ "$secs" -gt "$remaining" ]] && secs="$remaining"

	command_exists python3 || {
		echo "Cannot establish safe deadline: python3 unavailable"
		return 125
	}

	local tmp
	tmp=$(mktemp 2>/dev/null) || {
		echo "Cannot establish safe deadline: temporary file unavailable"
		return 125
	}
	local marker="${tmp}.timedout" overflow="${tmp}.overflow" pid="" watcher=""
	# shellcheck disable=SC2317,SC2329 # Invoked by cancellation traps in this subshell.
	cancel_lint_command() {
		[[ -z "$watcher" ]] || kill -KILL -- "-$watcher" 2>/dev/null
		if [[ -n "$pid" ]]; then
			kill -TERM -- "-$pid" 2>/dev/null
			kill -KILL -- "-$pid" 2>/dev/null
		fi
		rm -f "$tmp" "$marker" "$overflow"
		exit 143
	}
	trap cancel_lint_command HUP INT TERM

	set -m
	(
		set +m
		"$@" 2>&1 | python3 -I -S -c '
import os
import signal
import sys

limit = int(sys.argv[1])
written = 0
while True:
    chunk = os.read(0, 8192)
    if not chunk:
        break
    sys.stdout.buffer.write(chunk[:max(0, limit - written)])
    sys.stdout.buffer.flush()
    written += len(chunk)
    if written > limit:
        try:
            with open(sys.argv[2], "x"):
                pass
        except OSError:
            pass
        os.killpg(os.getpgrp(), signal.SIGKILL)

' "$SMART_LINT_OUTPUT_BYTES" "$overflow"
		codes=("${PIPESTATUS[@]}")
		[[ "${codes[1]}" -eq 0 ]] || exit 125
		exit "${codes[0]}"
	) >"$tmp" 2>/dev/null &
	pid=$!
	(
		set +m
		sleep "$secs"
		: >"$marker" 2>/dev/null
		kill -TERM -- "-$pid" 2>/dev/null
		sleep 2
		kill -KILL -- "-$pid" 2>/dev/null
	) </dev/null >/dev/null 2>&1 &
	watcher=$!
	local status=0
	wait "$pid" 2>/dev/null || status=$?
	if [[ ! -f "$marker" ]]; then kill -KILL -- "-$watcher" 2>/dev/null; fi
	wait "$watcher" 2>/dev/null

	local timed_out=0
	[[ ! -e "$marker" ]] || timed_out=1
	if [[ -e "$overflow" ]]; then
		printf '\nLinter output exceeded %s bytes\n' "$SMART_LINT_OUTPUT_BYTES"
		status=125
	fi
	cat "$tmp"
	rm -f "$tmp" "$marker" "$overflow"
	[[ "$timed_out" -eq 1 ]] && return 124
	return "$status"
) 2>/dev/null

# A run_with_timeout kill means the tool didn't finish in time -- not that
# its output showed a real problem. Turning that into a blocking error would
# recreate the kind of false block this hook exists to avoid (a cold or
# slow tool under load blocking an edit that has no lint issue at all), so a
# timeout is reported on stderr and does not fail the hook.
report_timeout() {
	local name="$1"
	SMART_LINT_TIMEOUT_COUNT=$((SMART_LINT_TIMEOUT_COUNT + 1))
	log_info "$name timed out and was skipped (not treated as a lint failure)"
}

report_check_problem() {
	local name="$1" code="$2" output="$3"
	if [[ "$code" -eq 124 ]]; then
		report_timeout "$name"
	elif [[ "$code" -eq 1 && -n "$output" ]]; then
		add_error "$name reported problems (exit $code)" "$(compact_output "$output")"
	else
		report_incomplete "$name exited $code: $(compact_output "$output")"
	fi
}

run_formatter_on_files() {
	local mode="check"
	if [[ "${1:-}" == "--format-only" ]]; then
		mode="format-only"
		shift
	fi

	local name="$1" format_cmd="$2" check_cmd="$3"
	shift 3
	local files=("$@")

	if [[ "${#files[@]}" -eq 0 ]]; then
		log_debug "No files to format, skipping $name"
		return 0
	fi

	log_debug "Running $name on files: ${files[*]}"
	mark_format_ran

	local output status
	# format_cmd/check_cmd are strings like "ruff format" that must split into
	# multiple words here; each caller controls its own value (no user input).
	# shellcheck disable=SC2086
	output=$(run_with_timeout "$SMART_LINT_CMD_TIMEOUT_SECONDS" $format_cmd "${files[@]}")
	status=$?
	if [[ "$status" -eq 124 ]]; then
		report_timeout "$name"
		return 0
	elif [[ "$status" -ne 0 ]]; then
		report_check_problem "$name" "$status" "$output"
		return 2
	fi

	if [[ "$mode" == "format-only" || -z "$check_cmd" ]]; then
		return 0
	fi

	# shellcheck disable=SC2086 # check_cmd is a multi-word string; see above.
	output=$(run_with_timeout "$SMART_LINT_CMD_TIMEOUT_SECONDS" $check_cmd "${files[@]}")
	status=$?
	if [[ "$status" -eq 0 ]]; then
		return 0
	elif [[ "$status" -eq 124 ]]; then
		report_timeout "$name"
	else
		report_check_problem "$name" "$status" "$output"
	fi
}

run_command_compact() {
	local name="$1"
	shift
	local output status
	output=$(run_with_timeout "$SMART_LINT_CMD_TIMEOUT_SECONDS" "$@")
	status=$?
	if [[ "$status" -eq 0 ]]; then
		log_debug "$name passed."
		return 0
	elif [[ "$status" -eq 124 ]]; then
		report_timeout "$name"
		return 0
	else
		report_check_problem "$name" "$status" "$output"
		return 2
	fi
}

run_linter_compact() {
	mark_lint_ran
	run_command_compact "$@"
}

run_linter() {
	run_linter_compact "$@"
}

run_package_lint_fallback() {
	project_fallback_enabled || return 0
	local script ran=0
	if [[ "$SMART_LINT_FORMAT_RAN" -eq 0 ]]; then
		for script in fmt format; do
			if run_package_script_compact "$script"; then
				mark_format_ran
				ran=1
				break
			fi
		done
	fi
	if [[ "$SMART_LINT_LINT_RAN" -eq 0 ]] && run_package_script_compact lint; then
		mark_lint_ran
		ran=1
	fi
	[[ "$ran" -eq 1 ]] || log_debug "No needed fmt/format/lint package scripts found"
}

run_make_lint_fallback() {
	project_fallback_enabled || return 0
	[[ -f "Makefile" ]] || return 0

	local ran=0
	if [[ "$SMART_LINT_FORMAT_RAN" -eq 0 ]] && grep -qE "^[[:space:]]*fmt[[:space:]]*:" Makefile 2>/dev/null; then
		mark_format_ran
		run_command_compact "make fmt" make fmt || true
		ran=1
	fi
	if [[ "$SMART_LINT_LINT_RAN" -eq 0 ]] && grep -qE "^[[:space:]]*lint[[:space:]]*:" Makefile 2>/dev/null; then
		mark_lint_ran
		run_command_compact "make lint" make lint || true
		ran=1
	fi
	[[ "$ran" -eq 1 ]] || log_debug "No needed fmt/lint Makefile targets found"
}

run_lint_fallbacks() {
	if ! project_fallback_enabled; then
		if [[ "$SMART_LINT_LINT_RAN" -eq 0 ]]; then
			log_info "unsupported: no focused linter ran; project fallback requires HOOK_PROJECT_FALLBACK=1"
		fi
		return 0
	fi
	local before="$SMART_LINT_LINT_RUNS" errors="${#ERRORS[@]}" incomplete="$SMART_LINT_INCOMPLETE_COUNT" timed_out="$SMART_LINT_TIMEOUT_COUNT"
	run_package_lint_fallback
	run_make_lint_fallback
	# An explicitly opted-in project lint command may cover missing focused tools.
	if [[ "$SMART_LINT_LINT_RUNS" -gt "$before" && "${#ERRORS[@]}" -eq "$errors" && "$SMART_LINT_INCOMPLETE_COUNT" -eq "$incomplete" && "$SMART_LINT_TIMEOUT_COUNT" -eq "$timed_out" ]]; then
		SMART_LINT_UNSUPPORTED=()
	fi
}

# Hash the exact content string (not the file) so the caller can verify and
# execute the same bytes, avoiding a check-then-read TOCTOU window.
project_hooks_config_content_trusted() {
	local content="$1" store="$HOME/.claude/trusted-hooks-config-hashes" hash
	[[ -f "$store" ]] || return 1
	if command_exists shasum; then
		hash=$(printf '%s' "$content" | shasum -a 256 2>/dev/null | awk '{print $1}')
	elif command_exists sha256sum; then
		hash=$(printf '%s' "$content" | sha256sum 2>/dev/null | awk '{print $1}')
	else
		return 1
	fi
	[[ -n "$hash" ]] || return 1
	grep -qxF "$hash" "$store" 2>/dev/null
}
