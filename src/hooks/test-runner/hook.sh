#!/usr/bin/env bash
# test-runner.sh - Focused test execution at agent-finish time.
#
# Runs tests causally related to edited files. Never runs a full project test
# suite unless TEST_RUNNER_FULL=1 is set explicitly. Python and Go tests
# run from their nearest project manifest directory, bounded by the hook cwd.
# Automatic feedback is advisory; explicit test commands and CI remain strict.

set +e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

export -n HOOK_INPUT_JSON
HOOK_INPUT_JSON="${HOOK_INPUT_JSON:-}"
HOOK_PROJECT_CWD=""
HOOK_SESSION_ID=default
PI_RUNTIME=0
HOOK_STATE_NAMESPACE=cc-thingz/hooks-v2
TEST_RUNNER_DIFF_FALLBACK_LIMIT="${TEST_RUNNER_DIFF_FALLBACK_LIMIT:-50}"
TEST_RUNNER_FULL="${TEST_RUNNER_FULL:-0}"
TEST_RUNNER_DEBUG="${TEST_RUNNER_DEBUG:-0}"
# Wall-clock budget for the whole hook run, in seconds, measured from process
# start via bash's builtin $SECONDS. Kept below the 120s harness timeout so a
# hung or slow suite is reported as "skipped: timeout" instead of the harness
# force-killing the hook with no output. An invalid value (empty, non-integer)
# falls back to the default; anything out of [1, 110] is clamped so a
# misconfigured value can't disable the budget or exceed the harness timeout.
TEST_RUNNER_TIMEOUT_SECS="${TEST_RUNNER_TIMEOUT_SECS:-90}"
TEST_RUNNER_COMPACT_LINES=120
TEST_RUNNER_OUTPUT_BYTES=1048576
HOOK_PROJECT_FALLBACK="${HOOK_PROJECT_FALLBACK:-0}"
TESTS_RAN=0
TESTS_PASSED=0
TESTS_COMMANDS_COMPLETED=0
TESTS_INCOMPLETE=0
RUN_TREE_FINGERPRINT=""
RUN_ATTEMPT_FINGERPRINT=""
TEST_REPORT_FILES=()
# Set when any test command was skipped for exceeding the timeout budget.
# main() must not clear the pending session state in that case — the
# untested files are still pending and must be retried on the next Stop.
TESTS_TIMED_OUT=0
log_debug() { [[ "$TEST_RUNNER_DEBUG" == "1" ]] && echo -e "${CYAN}[DEBUG]${NC} $*" >&2; }
log_info() { echo -e "${BLUE}[INFO]${NC} $*" >&2; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $*" >&2; }
command_exists() { command -v "$1" &>/dev/null; }
report_incomplete() {
	TESTS_INCOMPLETE=1
	log_warn "$*"
}

normalize_timeout() {
	case "$TEST_RUNNER_TIMEOUT_SECS" in
	'' | *[!0-9]*) TEST_RUNNER_TIMEOUT_SECS=90 ;;
	esac
	# Force base-10: a digits-only value with a leading zero (e.g. "008") is
	# otherwise read as octal by bash arithmetic, and "008" isn't even valid
	# octal, so the -lt/-gt comparisons below would error out instead of
	# clamping.
	TEST_RUNNER_TIMEOUT_SECS=$((10#$TEST_RUNNER_TIMEOUT_SECS))
	[[ "$TEST_RUNNER_TIMEOUT_SECS" -lt 1 ]] && TEST_RUNNER_TIMEOUT_SECS=1
	[[ "$TEST_RUNNER_TIMEOUT_SECS" -gt 110 ]] && TEST_RUNNER_TIMEOUT_SECS=110
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

package_json_has_script() {
	local script="$1"
	[[ -f package.json ]] || return 1
	if command_exists python3; then
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
' "$script" 2>/dev/null && return 0
	fi
	if command_exists node; then
		node -e '
const fs = require("fs");
const script = process.argv[process.argv.length - 1];
try {
  const data = JSON.parse(fs.readFileSync("package.json", "utf8"));
  process.exit(data && data.scripts && typeof data.scripts[script] === "string" ? 0 : 1);
} catch (_) {
  process.exit(1);
}
' "$script" 2>/dev/null && return 0
	fi
	if command_exists bun; then
		bun -e '
const fs = require("fs");
const script = process.argv[process.argv.length - 1];
try {
  const data = JSON.parse(fs.readFileSync("package.json", "utf8"));
  process.exit(data && data.scripts && typeof data.scripts[script] === "string" ? 0 : 1);
} catch (_) {
  process.exit(1);
}
' -- "$script" 2>/dev/null && return 0
	fi
	return 1
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

init_hook_input() {
	if [[ -z "$HOOK_INPUT_JSON" && ! -t 0 ]]; then
		if ! HOOK_INPUT_JSON=$(cat 2>/dev/null); then
			report_incomplete "Cannot read hook input; tests skipped"
			return 1
		fi
	fi
	if ! command_exists python3; then
		report_incomplete "Cannot read hook metadata: python3 unavailable; tests skipped"
		return 1
	fi
	{
		if ! IFS= read -r -d '' PI_RUNTIME ||
			! IFS= read -r -d '' HOOK_PROJECT_CWD ||
			! IFS= read -r -d '' HOOK_SESSION_ID; then
			report_incomplete "Cannot read hook metadata: invalid input or unusable python3; tests skipped"
			return 1
		fi
	} < <(python3 -I -S -c 'import json,os,sys
try:
    raw=sys.stdin.read()
    data=json.loads(raw if raw.strip() else "{}")
    if not isinstance(data, dict):
        sys.exit(1)
    pi=data.get("event") == "stop" and isinstance(data.get("piEvent"), dict)
    if data.get("event") == "stop" and "piEvent" in data and not pi:
        sys.exit(1)
    source=data["piEvent"] if pi else data
    vendor=data.get("vendorEvent") if isinstance(data.get("vendorEvent"), dict) else {}
    def field(name):
        value=source.get(name)
        return vendor.get(name) if value is None else value
    cwd=field("cwd")
    if cwd is not None and (not isinstance(cwd, str) or "\x00" in cwd or (cwd and not os.path.isdir(cwd))):
        sys.exit(1)
    sid=field("session_id")
    sid=str(sid) if sid is not None else "default"
    sid=sid.replace("\x00", "_") or "default"
    sys.stdout.write("\0".join([str(int(pi)), cwd or "", sid]) + "\0")
except Exception:
    sys.exit(1)
' <<<"$HOOK_INPUT_JSON" 2>/dev/null)
	case "$PI_RUNTIME" in
	0 | 1) ;;
	*)
		report_incomplete "Invalid hook metadata response; tests skipped"
		return 1
		;;
	esac
	return 0
}

finish_hook() {
	trap - EXIT
	[[ "${#TEST_REPORT_FILES[@]}" -eq 0 ]] || rm -f -- "${TEST_REPORT_FILES[@]}"
	[[ "$PI_RUNTIME" == "1" ]] && echo '{"decision":"allow"}'
	exit 0
}

# shellcheck disable=SC2317,SC2329 # Invoked by the EXIT trap, including unexpected failures.
unexpected_hook_exit() {
	local code="$1"
	[[ "$code" -eq 0 ]] || log_warn "Test hook internal error (exit $code); results incomplete, agent may continue"
	finish_hook
}

maybe_cd_to_hook_cwd() {
	if [[ -n "$HOOK_PROJECT_CWD" ]] && ! cd "$HOOK_PROJECT_CWD"; then
		report_incomplete "Cannot enter hook project cwd; tests skipped"
		return 1
	fi
	return 0
}

hook_session_id() {
	printf '%s\n' "$HOOK_SESSION_ID"
}

hook_state_path() {
	git rev-parse --git-dir >/dev/null 2>&1 || return 1
	local session_id safe_session_id scope
	scope=$(git rev-parse --show-prefix 2>/dev/null) || return 1
	session_id=$(hook_session_id)
	safe_session_id=$(printf '%s' "$session_id" | tr -c 'A-Za-z0-9_.-' '_')
	git rev-parse --git-path "$HOOK_STATE_NAMESPACE/${scope}hook-files-${safe_session_id:-default}" 2>/dev/null
}

# Separate from hook_state_path: a snapshot of the working tree at the moment
# the session state was last cleared, so a later Stop can tell "still exactly
# what I already tested" (skip) from "something changed that smart-lint never
# recorded" (fall back to a git diff), instead of trusting an empty state file
# blindly. See tree_fingerprint() and tree_unchanged_since_last_run().
hook_fingerprint_path() {
	git rev-parse --git-dir >/dev/null 2>&1 || return 1
	local session_id safe_session_id scope
	scope=$(git rev-parse --show-prefix 2>/dev/null) || return 1
	session_id=$(hook_session_id)
	safe_session_id=$(printf '%s' "$session_id" | tr -c 'A-Za-z0-9_.-' '_')
	git rev-parse --git-path "$HOOK_STATE_NAMESPACE/${scope}hook-tree-${safe_session_id:-default}" 2>/dev/null
}

is_subagent_child() {
	[[ "${PI_SUBAGENT_CHILD:-}" == "1" ]]
}

# Snapshot code/config changes, including untracked file contents. An attempt
# is not a pass: keep pending files after problems but don't repeat unchanged
# failures on every Stop. Explicit TEST_RUNNER_FULL bypasses attempt suppression.
tree_fingerprint() {
	git rev-parse --git-dir >/dev/null 2>&1 || return 1
	{
		git diff --relative --no-ext-diff HEAD 2>/dev/null || true
		git ls-files --others --exclude-standard 2>/dev/null | sort | while IFS= read -r file; do
			path_is_excluded "$file" && continue
			if ! has_code_extension "$file"; then
				case "${file##*/}" in
				pyproject.toml | uv.lock | package.json | go.mod | go.sum | go.work | go.work.sum | bun.lock | bun.lockb | yarn.lock | package-lock.json | pnpm-lock.yaml | pnpm-workspace.yaml) ;;
				*) continue ;;
				esac
			fi
			printf '%s\n' "$file"
			[[ -f "$file" ]] && cksum <"$file"
		done
	} | cksum 2>/dev/null
}

# True when the working tree matches the fingerprint taken the last time
# clear_hook_state() concluded a run — i.e. nothing changed since, including
# edits smart-lint never recorded (Bash tool: sed -i, git apply, codegen).
tree_unchanged_since_last_run() {
	local fp_path stored current
	fp_path=$(hook_fingerprint_path 2>/dev/null || true)
	[[ -n "$fp_path" && -f "$fp_path" ]] || return 1
	stored=$(cat "$fp_path" 2>/dev/null)
	[[ -n "$stored" ]] || return 1
	current=$(tree_fingerprint)
	[[ -n "$current" && "$current" == "$stored" ]]
}

hook_attempt_path() {
	local state
	state=$(hook_state_path) || return 1
	printf '%s.attempt\n' "$state"
}

attempt_fingerprint() {
	local state
	{
		printf '%s\n' "$RUN_TREE_FINGERPRINT" "$HOOK_PROJECT_FALLBACK" "$TEST_RUNNER_TIMEOUT_SECS" "$TEST_RUNNER_DIFF_FALLBACK_LIMIT"
		state=$(hook_state_path 2>/dev/null || true)
		[[ -z "$state" || ! -f "$state" ]] || cksum <"$state"
	} | cksum
}

previous_attempt_matches() {
	local path previous
	path=$(hook_attempt_path) || return 1
	[[ -f "$path" && -n "$RUN_ATTEMPT_FINGERPRINT" ]] || return 1
	IFS= read -r previous <"$path"
	[[ "$previous" == "$RUN_ATTEMPT_FINGERPRINT" ]]
}

record_incomplete_attempt() {
	local path
	path=$(hook_attempt_path) || return 0
	[[ -n "$RUN_ATTEMPT_FINGERPRINT" ]] || return 0
	mkdir -p "$(dirname "$path")" 2>/dev/null || return 0
	printf '%s\n' "$RUN_ATTEMPT_FINGERPRINT" >"$path"
}

clear_hook_state() {
	# Truncate rather than remove the file list: an empty state file tells
	# the next Stop "nothing recorded as pending", so collect_focus_files
	# falls through to the fingerprint check below instead of trusting an
	# absent file straight into a git diff fallback that would re-run tests
	# for every still-dirty file.
	local state_path state_dir fp_path attempt_path
	attempt_path=$(hook_attempt_path 2>/dev/null || true)
	[[ -z "$attempt_path" ]] || rm -f "$attempt_path"
	state_path=$(hook_state_path 2>/dev/null || true)
	if [[ -n "$state_path" ]]; then
		state_dir=$(dirname "$state_path")
		mkdir -p "$state_dir" 2>/dev/null && : >"$state_path" 2>/dev/null
	fi
	# Snapshot the tree we just finished testing, so the next Stop can tell
	# a genuine no-op from an untracked edit smart-lint never saw.
	fp_path=$(hook_fingerprint_path 2>/dev/null || true)
	[[ -n "$fp_path" ]] || return 0
	mkdir -p "$(dirname "$fp_path")" 2>/dev/null || return 0
	if [[ -n "$RUN_TREE_FINGERPRINT" ]]; then
		printf '%s\n' "$RUN_TREE_FINGERPRINT" >"$fp_path"
	else
		tree_fingerprint >"$fp_path" 2>/dev/null
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

has_code_extension() {
	case "$1" in
	*.py | *.go | *.rs | *.cs | *.csproj | *.sln | *.props | *.targets | *.java | *.kt | *.kts | *.js | *.jsx | *.ts | *.tsx | *.mjs | *.cjs | *.mts | *.cts | *.sh | *.bash | *.bats | \
		Cargo.toml | Cargo.lock | rust-toolchain | rust-toolchain.toml | pom.xml | build.gradle | settings.gradle | gradle.properties) return 0 ;;
	*) return 1 ;;
	esac
}

diff_fallback_files() {
	git rev-parse --git-dir >/dev/null 2>&1 || return 0
	{
		git diff --relative --name-only --diff-filter=ACMRTUXB --cached HEAD 2>/dev/null || true
		git diff --relative --name-only --diff-filter=ACMRTUXB 2>/dev/null || true
		git ls-files --others --exclude-standard 2>/dev/null || true
	} | sort -u
}

# Canonicalize the parent directory so absolute paths and ../ aliases cannot
# select a project above the hook cwd, including through directory symlinks.
hook_relative_file() {
	local root="$1" file="$2" dir relative_dir
	dir=$(cd -P -- "$(dirname "$file")" 2>/dev/null && pwd -P) || return 1
	case "$dir/" in
	"$root/"*) ;;
	*) return 1 ;;
	esac
	relative_dir=${dir#"$root"}
	relative_dir=${relative_dir#/}
	printf '%s\n' "${relative_dir:+$relative_dir/}${file##*/}"
}

collect_focus_files() {
	local state_path file count hook_root source="session state"
	hook_root=$(pwd -P)
	local tmp_raw tmp_filtered
	state_path=$(hook_state_path 2>/dev/null || true)
	tmp_raw=$(mktemp 2>/dev/null) || {
		log_warn "Temporary file unavailable; checks incomplete"
		return 2
	}
	tmp_filtered=$(mktemp 2>/dev/null) || {
		rm -f "$tmp_raw"
		log_warn "Temporary file unavailable; checks incomplete"
		return 2
	}
	if [[ -n "$state_path" && -s "$state_path" ]]; then
		# Recorded edits take precedence over the fingerprint check below.
		cat "$state_path" >"$tmp_raw"
	elif [[ -n "$state_path" && -f "$state_path" ]] && tree_unchanged_since_last_run; then
		# The state file exists but is empty (clear_hook_state concluded a
		# run) and the tree still matches that moment's fingerprint: nothing
		# changed since, including edits smart-lint doesn't track (Bash
		# tool: sed -i, git apply, codegen). Genuinely nothing to test.
		source="session state (tree unchanged since last run)"
		: >"$tmp_raw"
	elif is_subagent_child; then
		source="subagent child without hook state"
		: >"$tmp_raw"
	else
		source="git diff fallback"
		diff_fallback_files >"$tmp_raw"
	fi
	while IFS= read -r file; do
		[[ -n "$file" ]] || continue
		file=$(hook_relative_file "$hook_root" "$file") || continue
		[[ -f "$file" ]] || continue
		path_is_excluded "$file" && continue
		has_code_extension "$file" || continue
		printf '%s\n' "$file"
	done <"$tmp_raw" | sort -u >"$tmp_filtered"
	count=$(wc -l <"$tmp_filtered" 2>/dev/null | tr -d ' ')
	if [[ "$source" == "git diff fallback" && "$count" -gt "$TEST_RUNNER_DIFF_FALLBACK_LIMIT" ]]; then
		report_incomplete "Skipping focused tests: diff fallback exceeded TEST_RUNNER_DIFF_FALLBACK_LIMIT=$TEST_RUNNER_DIFF_FALLBACK_LIMIT"
		rm -f "$tmp_raw" "$tmp_filtered"
		return 2
	fi
	cat "$tmp_filtered"
	rm -f "$tmp_raw" "$tmp_filtered"
	log_debug "Focus-file source: $source"
	return 0
}

unique_lines() {
	sort -u | sed '/^$/d'
}

run_package_test_script() {
	local script="$1" runner kind bin
	package_json_has_script "$script" || return 1
	runner=$(package_script_runner || true)
	[[ -n "$runner" ]] || return 1
	kind=${runner%%|*}
	bin=${runner#*|}
	case "$kind" in
	yarn) run_and_capture "yarn $script" "$bin" run "$script" ;;
	bun) run_and_capture "bun $script" "$bin" run "$script" ;;
	npm) run_and_capture "npm $script" "$bin" run --silent "$script" ;;
	*) return 1 ;;
	esac
}

run_package_test_fallback() {
	project_fallback_enabled || return 0
	[[ "$TESTS_RAN" -eq 0 ]] || return 0
	local script
	for script in test tests check verify; do
		package_json_has_script "$script" || continue
		run_package_test_script "$script"
		return $?
	done
	log_debug "No test/tests/check/verify package scripts found"
	return 0
}

nearest_non_root_makefile_for_file() {
	local file="$1" dir
	dir=$(dirname "$file")
	while [[ -n "$dir" && "$dir" != "." && "$dir" != "/" ]]; do
		if [[ -f "$dir/Makefile" ]]; then
			printf '%s\n' "$dir/Makefile"
			return 0
		fi
		dir=$(dirname "$dir")
	done
	return 1
}

makefile_target_for_path() {
	local makefile="$1" target
	for target in test tests check verify; do
		if grep -qE "^[[:space:]]*${target}[[:space:]]*:" "$makefile" 2>/dev/null; then
			printf '%s\n' "$target"
			return 0
		fi
	done
	return 1
}

run_nearest_makefile_tests() {
	MAKEFILE_COVERED_FILES=()
	project_fallback_enabled || return 0
	local focus_files=("$@")
	local dir makefile target status=0 file pairs=""
	for file in "${focus_files[@]}"; do
		makefile=$(nearest_non_root_makefile_for_file "$file" || true)
		[[ -n "$makefile" ]] || continue
		target=$(makefile_target_for_path "$makefile" || true)
		[[ -n "$target" ]] || continue
		MAKEFILE_COVERED_FILES+=("$file")
		dir=$(dirname "$makefile")
		pairs+="$dir|$target"$'\n'
	done
	[[ -n "$pairs" ]] || return 0
	while IFS='|' read -r dir target; do
		[[ -n "$dir" && -n "$target" ]] || continue
		run_and_capture "make $target" make -C "$dir" "$target" || status=2
	done < <(printf '%s' "$pairs" | sort -u)
	return "$status"
}

compact_output() {
	local max_lines="$TEST_RUNNER_COMPACT_LINES" max_bytes=8000
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

# Runs "$@" in its own process group with a wall-clock deadline of $1 seconds,
# so a hung or slow test process — and any children it spawns, e.g. `go build`,
# `uv sync`, a Gradle daemon — cannot hold the Stop hook past its own timeout.
# Prints the command's combined stdout/stderr; returns 124 if the deadline
# fired, else the command's own exit code.
run_with_deadline() {
	local budget="$1"
	shift
	local outfile timeout_flag overflow_flag code
	command_exists python3 || {
		echo "Cannot safely capture test output: python3 unavailable"
		return 125
	}
	outfile=$(mktemp 2>/dev/null) || {
		echo "Cannot create test output file"
		return 125
	}
	timeout_flag=$(mktemp 2>/dev/null) || {
		rm -f "$outfile"
		echo "Cannot create test deadline file"
		return 125
	}
	overflow_flag="$timeout_flag.overflow"
	rm -f "$timeout_flag" "$overflow_flag"
	(
		cmd_pid="" watchdog_pid=""
		# shellcheck disable=SC2317,SC2329 # Invoked by the cancellation traps in this subshell.
		cancel_test_jobs() {
			# These jobs have separate process groups, outside the adapter's
			# hook group. An adapter cancellation must not orphan them.
			if [[ -n "$watchdog_pid" ]]; then kill -KILL -- "-$watchdog_pid" 2>/dev/null; fi
			if [[ -n "$cmd_pid" ]]; then
				kill -TERM -- "-$cmd_pid" 2>/dev/null
				kill -KILL -- "-$cmd_pid" 2>/dev/null
			fi
			rm -f "$outfile" "$timeout_flag" "$overflow_flag"
			exit 143
		}
		trap cancel_test_jobs HUP INT TERM
		# set -m gives "$@" its own process group so the watchdog can kill
		# the whole tree; it also makes bash announce job state changes
		# ("[1]+ Terminated ...") on this subshell's stderr, which is not
		# part of the command's own output — redirected away below.
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

' "$TEST_RUNNER_OUTPUT_BYTES" "$overflow_flag"
			codes=("${PIPESTATUS[@]}")
			[[ "${codes[1]}" -eq 0 ]] || exit 125
			exit "${codes[0]}"
		) >"$outfile" 2>/dev/null &
		cmd_pid=$!
		(
			set +m
			sleep "$budget"
			: >"$timeout_flag"
			kill -TERM -- "-$cmd_pid" 2>/dev/null
			sleep 2
			kill -KILL -- "-$cmd_pid" 2>/dev/null
		) </dev/null >/dev/null 2>&1 &
		watchdog_pid=$!
		wait "$cmd_pid"
		cmd_status=$?
		# Cancel the entire watchdog job, including sleep, after normal completion.
		# Once the deadline fires, let its KILL escalation finish for descendants.
		if [[ ! -f "$timeout_flag" ]]; then
			kill -TERM -- "-$watchdog_pid" 2>/dev/null
		fi
		wait "$watchdog_pid" 2>/dev/null
		exit "$cmd_status"
	) 2>/dev/null
	code=$?
	# Only classify as a timeout if the watchdog actually fired AND the exit
	# code shows the process died to a signal (>128) — otherwise a command
	# that happened to finish in the narrow window between the watchdog
	# writing its flag and sending the kill would be misreported as timed
	# out instead of using its real (successful) exit code.
	if [[ -f "$timeout_flag" && "$code" -gt 128 ]]; then
		code=124
	fi
	if [[ -e "$overflow_flag" ]]; then
		printf '\nTest command output exceeded %s bytes\n' "$TEST_RUNNER_OUTPUT_BYTES"
		code=125
	fi
	cat "$outfile" 2>/dev/null
	rm -f "$outfile" "$timeout_flag" "$overflow_flag"
	return "$code"
}

# Remaining seconds in the hook's wall-clock budget, measured from process
# start via bash's builtin $SECONDS. Zero or negative means the budget is
# exhausted and no further test command should start.
remaining_budget() {
	printf '%d\n' "$((TEST_RUNNER_TIMEOUT_SECS - SECONDS))"
}

run_test_compact() {
	local label="$1" report_kind="$2" report_file="$3"
	shift 3
	local remaining
	remaining=$(remaining_budget)
	if [[ "$remaining" -le 0 ]]; then
		TESTS_TIMED_OUT=1
		log_warn "skipped: timeout — no budget left to run $label"
		return 0
	fi
	TESTS_RAN=1
	log_info "Running: $*"
	local output="" code
	if [[ "$report_kind" == go-json ]]; then
		report_file=$(mktemp 2>/dev/null) || {
			report_incomplete "Cannot create Go test report file"
			return 0
		}
		TEST_REPORT_FILES+=("$report_file")
		run_with_deadline "$remaining" "$@" >"$report_file"
		code=$?
	else
		output=$(run_with_deadline "$remaining" "$@")
		code=$?
	fi
	if [[ "$code" -eq 124 ]]; then
		TESTS_TIMED_OUT=1
		log_warn "skipped: timeout — $label exceeded ${TEST_RUNNER_TIMEOUT_SECS}s budget"
		[[ -n "$output" ]] && compact_output "$output" >&2
		return 0
	fi
	if [[ "$code" -eq 125 ]]; then
		report_incomplete "$label: command capture unavailable or output limit exceeded (exit 125)"
		if [[ "$report_kind" == go-json ]]; then output=$(head -c 8192 "$report_file"); fi
		[[ -z "$output" ]] || compact_output "$output" >&2
		return 0
	fi

	if [[ -n "$report_kind" ]]; then
		local summary summary_code executed failed diagnostics
		remaining=$(remaining_budget)
		if [[ "$remaining" -le 0 ]]; then
			TESTS_TIMED_OUT=1
			report_incomplete "$label: timeout before test results could be verified"
			return 0
		fi
		summary=$(run_with_deadline "$remaining" python3 -I -S "$HOOK_SCRIPT_DIR/parse-report.py" "$report_kind" "$report_file" <<<"$output")
		summary_code=$?
		if [[ "$summary_code" -ne 0 ]]; then
			[[ "$summary_code" -ne 124 ]] || TESTS_TIMED_OUT=1
			report_incomplete "$label: $(compact_output "$summary")"
			if [[ "$report_kind" == go-json ]]; then output=$(head -c 8192 "$report_file"); fi
			[[ -z "$output" ]] || compact_output "$output" >&2
			[[ "$code" -eq 0 ]] && return 0 || return 2
		fi
		read -r executed failed <<<"${summary%%$'\n'*}"
		diagnostics=""
		[[ "$summary" != *$'\n'* ]] || diagnostics=${summary#*$'\n'}
		if [[ "$report_kind" == go-json ]]; then
			output="$diagnostics"
		elif [[ -n "$diagnostics" ]]; then
			output+=$'\n'"$diagnostics"
		fi
		if [[ "$code" -eq 0 && "$failed" -gt 0 ]]; then
			report_incomplete "$label: report contains failed tests despite exit 0"
			[[ -z "$output" ]] || compact_output "$output" >&2
			return 0
		fi
		if [[ "$code" -eq 0 && "$executed" -eq 0 ]]; then
			report_incomplete "$label: no tests executed"
			return 0
		fi
	fi

	if [[ "$code" -eq 0 ]]; then
		if [[ -z "$report_kind" ]]; then
			TESTS_COMMANDS_COMPLETED=1
			report_incomplete "$label completed with exit 0; test collection is not verified for this runner"
		else
			TESTS_PASSED=1
		fi
		log_debug "$label completed"
		return 0
	fi
	log_warn "$label failed with exit $code"
	[[ -n "$output" ]] && compact_output "$output" >&2
	return 2
}

run_and_capture() {
	local label="$1" kind=""
	shift
	if [[ "$1" == go && "${2:-}" == test ]]; then kind=go-json; fi
	run_test_compact "$label" "$kind" "" "$@"
}

run_js_reported_tests() {
	local label="$1" kind="$2" report code
	shift 2
	report=$(mktemp 2>/dev/null) || {
		report_incomplete "Cannot create JS test report file"
		return 0
	}
	TEST_REPORT_FILES+=("$report")
	case "$kind" in
	vitest) run_test_compact "$label" js-json "$report" "$@" --reporter=json "--outputFile=$report" ;;
	jest) run_test_compact "$label" js-json "$report" "$@" --json "--outputFile=$report" ;;
	bun) run_test_compact "$label" bun-junit "$report" "$@" --reporter=junit "--reporter-outfile=$report" ;;
	esac
	code=$?
	rm -f "$report"
	return "$code"
}

# Like run_test_compact, but treats pytest exit code 5 ("no tests collected")
# as skipped — handing pytest a file with no test functions is not a failure.
run_pytest_compact() {
	local label="$1"
	shift
	local remaining
	remaining=$(remaining_budget)
	if [[ "$remaining" -le 0 ]]; then
		TESTS_TIMED_OUT=1
		log_warn "skipped: timeout — no budget left to run $label"
		return 0
	fi
	TESTS_RAN=1
	log_info "Running: $*"
	local output code
	output=$(run_with_deadline "$remaining" "$@")
	code=$?
	if [[ "$code" -eq 124 ]]; then
		TESTS_TIMED_OUT=1
		log_warn "skipped: timeout — $label exceeded ${TEST_RUNNER_TIMEOUT_SECS}s budget"
		[[ -n "$output" ]] && compact_output "$output" >&2
		return 0
	fi
	if [[ "$code" -eq 5 ]]; then
		TESTS_INCOMPLETE=1
		log_info "skipped: $label collected no tests"
		return 0
	fi
	if [[ "$code" -eq 0 ]]; then
		TESTS_PASSED=1
		log_debug "$label passed"
		return 0
	fi
	log_warn "$label failed with exit $code"
	[[ -n "$output" ]] && compact_output "$output" >&2
	return 2
}

add_existing_file() {
	local candidate="$1"
	[[ -f "$candidate" ]] && printf '%s\n' "$candidate"
}

# shellcheck disable=SC2317,SC2329 # Invoked as a function command by run_with_deadline.
uv_pytest_prefix_args() {
	[[ -f pyproject.toml ]] || return 1
	command_exists python3 || return 1
	python3 - <<'PY' 2>/dev/null
import re
import sys
from pathlib import Path


def read_pyproject():
    try:
        text = Path("pyproject.toml").read_text()
    except OSError:
        sys.exit(1)
    data = parse_with_toml(text)
    if data is not None:
        return data
    return parse_light_toml(text)


def parse_with_toml(text):
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib
        except ImportError:
            return None
    try:
        return tomllib.loads(text)
    except Exception:
        return None


def strip_comment(line):
    result = []
    quote = ""
    escaped = False
    for char in line:
        if quote:
            result.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = ""
            continue
        if char in "'\"":
            quote = char
            result.append(char)
            continue
        if char == "#":
            break
        result.append(char)
    return "".join(result)


def parse_light_toml(text):
    data = {"project": {"dependencies": [], "optional-dependencies": {}}, "dependency-groups": {}}
    section = ""
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        line = strip_comment(lines[index]).strip()
        index += 1
        if not line:
            continue
        match = re.match(r"\[([^\]]+)\]\s*$", line)
        if match:
            section = match.group(1).strip().strip("'\"")
            continue
        match = re.match(r"([A-Za-z0-9_.-]+|'[^']+'|\"[^\"]+\")\s*=\s*(.*)$", line)
        if not match:
            continue
        key = match.group(1).strip().strip("'\"")
        value = match.group(2)
        if "[" not in value:
            continue
        buffer = value
        depth = value.count("[") - value.count("]")
        while depth > 0 and index < len(lines):
            next_line = strip_comment(lines[index])
            index += 1
            buffer += "\n" + next_line
            depth += next_line.count("[") - next_line.count("]")
        deps = re.findall(r"['\"]([^'\"]+)['\"]", buffer)
        if section == "project" and key == "dependencies":
            data["project"]["dependencies"] = deps
        elif section == "project.optional-dependencies":
            data["project"]["optional-dependencies"][key] = deps
        elif section == "dependency-groups":
            data["dependency-groups"][key] = deps
    return data


def dep_name(value):
    if not isinstance(value, str):
        return ""
    return re.split(r"[<>=!~; \\[]", value.strip(), maxsplit=1)[0].lower().replace("_", "-")


def is_pytest_dep(value):
    name = dep_name(value)
    return name == "pytest" or name.startswith("pytest-")


def contains_pytest(value):
    if isinstance(value, str):
        return is_pytest_dep(value)
    if isinstance(value, list):
        return any(contains_pytest(item) for item in value)
    if isinstance(value, dict):
        return any(contains_pytest(item) for item in value.values())
    return False


def choose_name(names):
    for preferred in ("test", "tests", "dev", "ci"):
        if preferred in names:
            return preferred
    return sorted(names)[0] if names else ""


def group_contains_pytest(groups, name, seen=None):
    if seen is None:
        seen = set()
    if name in seen:
        return False
    seen.add(name)
    deps = groups.get(name)
    if contains_pytest(deps):
        return True
    if isinstance(deps, list):
        for item in deps:
            if isinstance(item, dict):
                included = item.get("include-group")
                if isinstance(included, str) and group_contains_pytest(groups, included, seen):
                    return True
    return False


data = read_pyproject()
project = data.get("project", {})
if contains_pytest(project.get("dependencies", [])):
    print("run")
    sys.exit(0)

optional_deps = project.get("optional-dependencies", {})
if isinstance(optional_deps, dict):
    extras = [name for name, deps in optional_deps.items() if contains_pytest(deps)]
    extra = choose_name(extras)
    if extra:
        print("run")
        print("--extra")
        print(extra)
        sys.exit(0)

groups = data.get("dependency-groups", {})
if isinstance(groups, dict):
    group_names = [name for name in groups if group_contains_pytest(groups, name)]
    group = choose_name(group_names)
    if group:
        print("run")
        print("--group")
        print(group)
        sys.exit(0)

# Workspace dev dependencies may live only at the workspace root. Detect an
# existing workspace environment, then let uv itself confirm membership and
# interpreter selection in the bounded no-sync import probe. Never guess globs.
for directory in Path.cwd().parents:
    manifest = directory / "pyproject.toml"
    try:
        text = manifest.read_text()
    except OSError:
        continue
    parent = parse_with_toml(text)
    if isinstance(parent, dict):
        tools = parent.get("tool", {})
        uv = tools.get("uv", {}) if isinstance(tools, dict) else {}
        workspace = uv.get("workspace") if isinstance(uv, dict) else None
        is_workspace = isinstance(workspace, dict)
    else:
        is_workspace = bool(re.search(r"(?m)^\s*\[tool\.uv\.workspace\]", text))
    if is_workspace and (directory / ".venv" / "bin" / "pytest").is_file():
        print("run")
        sys.exit(0)

sys.exit(1)
PY
}

pytest_runner_command() {
	local -x UV_NO_SYNC=1
	local arg prefix probe_code remaining uv_args=()
	if command_exists uv && [[ -f pyproject.toml ]]; then
		remaining=$(remaining_budget)
		[[ "$remaining" -gt 0 ]] || return 124
		prefix=$(run_with_deadline "$remaining" uv_pytest_prefix_args)
		probe_code=$?
		[[ "$probe_code" -ne 124 ]] || return 124
		[[ "$probe_code" -ne 125 ]] || return 125
		[[ "$probe_code" -eq 0 ]] || prefix=""
		while IFS= read -r arg; do
			[[ -n "$arg" ]] && uv_args+=("$arg")
		done <<<"$prefix"
		if [[ "${#uv_args[@]}" -gt 0 ]]; then
			remaining=$(remaining_budget)
			[[ "$remaining" -gt 0 ]] || return 124
			run_with_deadline "$remaining" uv "${uv_args[@]}" python -c 'import pytest' >/dev/null 2>&1
			probe_code=$?
			[[ "$probe_code" -ne 124 ]] || return 124
			if [[ "$probe_code" -eq 0 ]]; then
				printf '%s\n' uv "${uv_args[@]}" pytest
				return 0
			fi
		fi
	fi
	if [[ -x .venv/bin/pytest ]]; then
		printf '%s\n' .venv/bin/pytest
		return 0
	fi
	if command_exists python3; then
		remaining=$(remaining_budget)
		[[ "$remaining" -gt 0 ]] || return 124
		run_with_deadline "$remaining" python3 -c "import pytest" >/dev/null 2>&1
		probe_code=$?
		[[ "$probe_code" -ne 124 ]] || return 124
		if [[ "$probe_code" -eq 0 ]]; then
			printf '%s\n' python3 -m pytest
			return 0
		fi
	fi
	return 1
}

# Inputs are hook-relative paths. Never inherit a project above the hook cwd.
nearest_project_root() {
	local file="$1" manifest="$2" dir
	dir=$(dirname "$file")
	while [[ "$dir" != "." && "$dir" != "/" ]]; do
		if [[ -f "$dir/$manifest" ]]; then
			printf '%s\n' "$dir"
			return 0
		fi
		dir=$(dirname "$dir")
	done
	printf '.\n'
}

# Keep execution in this shell: test counters and timeout state must survive
# each project. Only nested groups add a label, preserving root-only output.
run_project_test_groups() {
	local manifest="$1"
	shift
	local files=("$@") roots=() owners=() group=()
	local file root owner old_pwd="$PWD" i status=0
	[[ "${#files[@]}" -gt 0 ]] || return 0
	for file in "${files[@]}"; do
		if [[ "$manifest" == package.json ]]; then
			root=$(js_effective_project_root "$file")
		else
			root=$(nearest_project_root "$file" "$manifest")
		fi
		owners+=("$root")
		roots+=("$root")
	done
	while IFS= read -r root; do
		group=()
		for ((i = 0; i < ${#files[@]}; i++)); do
			owner=${owners[i]}
			[[ "$owner" == "$root" ]] || continue
			file=${files[i]}
			[[ "$root" == "." ]] || file=${file#"$root/"}
			group+=("$file")
		done
		if ! cd "$old_pwd/$root"; then
			status=2
			continue
		fi
		case "$manifest" in
		pyproject.toml) run_python_project_tests "$root" "${group[@]}" || status=2 ;;
		go.mod) run_go_project_tests "$root" "${group[@]}" || status=2 ;;
		package.json) run_javascript_project_tests "$root" "${group[@]}" || status=2 ;;
		esac
		cd "$old_pwd" || return 2
	done < <(printf '%s\n' "${roots[@]}" | unique_lines)
	return "$status"
}

run_python_tests() {
	local files=() file
	for file in "$@"; do
		[[ "$file" == *.py ]] && files+=("$file")
	done
	run_project_test_groups pyproject.toml "${files[@]}"
}

find_python_tests_for_source() {
	local file="$1" index="$2" dir base candidate candidate_base
	dir=$(dirname "$file")
	base=${file##*/}
	base=${base%.py}
	add_existing_file "$dir/test_${base}.py"
	add_existing_file "$dir/${base}_test.py"
	while IFS= read -r candidate; do
		[[ -n "$candidate" ]] || continue
		candidate_base=${candidate##*/}
		if [[ "$candidate_base" == "test_${base}.py" || "$candidate_base" == "${base}_test.py" ]]; then
			printf '%s\n' "$candidate"
		fi
	done <"$index"
}

# shellcheck disable=SC2317,SC2329 # Invoked under the shared command deadline.
index_python_tests() (
	set -o pipefail
	find . -type d \( -name .git -o -name .venv -o -name venv -o -name node_modules -o -name vendor -o -name dist -o -name build -o -name .tox -o -name __pycache__ \) -prune -o \
		-type d ! -path . -exec test -f '{}/pyproject.toml' \; -prune -o \
		-type f \( -name 'test_*.py' -o -name '*_test.py' \) -print |
		while IFS= read -r candidate; do
			candidate=${candidate#./}
			case "$candidate" in tests/* | test/* | */tests/* | */test/*) printf '%s\n' "$candidate" ;; esac
		done
)

run_python_project_tests() {
	local root="$1"
	shift
	[[ "$root" == "." ]] || log_info "Python tests in $root"
	# uv may select an existing environment, but must never sync/install into it.
	local -x UV_NO_SYNC=1
	local focus_files=("$@")
	local tests=()
	local file base tmp runner=() candidate_index selection selection_code before
	local needs_mapping=0 remaining discovery_code
	for file in "${focus_files[@]}"; do
		base=${file##*/}
		case "$base" in test_*.py | *_test.py) ;; *) needs_mapping=1 ;; esac
	done
	candidate_index=$(mktemp 2>/dev/null) || {
		report_incomplete "Cannot index Python tests: temporary file unavailable"
		return 0
	}
	if [[ "$needs_mapping" -eq 1 ]]; then
		remaining=$(remaining_budget)
		if [[ "$remaining" -le 0 ]]; then
			TESTS_TIMED_OUT=1
			report_incomplete "Python test discovery skipped: timeout in $root"
			rm -f "$candidate_index"
			return 0
		fi
		run_with_deadline "$remaining" index_python_tests >"$candidate_index"
		discovery_code=$?
		if [[ "$discovery_code" -ne 0 ]]; then
			[[ "$discovery_code" -ne 124 ]] || TESTS_TIMED_OUT=1
			report_incomplete "Python test discovery incomplete in $root (exit $discovery_code)"
			rm -f "$candidate_index"
			return 0
		fi
	fi
	for file in "${focus_files[@]}"; do
		[[ "$file" == *.py ]] || continue
		base=${file##*/}
		# Only genuine pytest test modules (test_*.py / *_test.py) are valid
		# targets. Support files under a test dir — conftest.py, __init__.py,
		# fixtures/helpers — are NOT test modules; passing them to pytest
		# collects nothing (exit 5). Route everything else through source
		# mapping, which finds the related test module if one exists.
		if [[ "$base" == test_*.py || "$base" == *_test.py ]]; then
			tests+=("$file")
		else
			before=${#tests[@]}
			while IFS= read -r candidate; do
				[[ -n "$candidate" ]] && tests+=("$candidate")
			done < <(find_python_tests_for_source "$file" "$candidate_index")
			[[ "${#tests[@]}" -gt "$before" ]] || report_incomplete "No focused Python tests found for $file in $root"
		fi
	done
	rm -f "$candidate_index"
	[[ "${#tests[@]}" -gt 0 ]] || return 0
	tmp=$(mktemp 2>/dev/null) || {
		log_warn "Temporary file unavailable; checks incomplete"
		return 2
	}
	printf '%s\n' "${tests[@]}" | unique_lines >"$tmp"
	tests=()
	while IFS= read -r file; do tests+=("$file"); done <"$tmp"
	rm -f "$tmp"
	selection=$(pytest_runner_command)
	selection_code=$?
	if [[ "$selection_code" -ne 0 && "$selection_code" -ne 1 && "$selection_code" -ne 124 ]]; then
		report_incomplete "Cannot select Python environment in $root (exit $selection_code)"
		return 0
	fi
	if [[ "$selection_code" -eq 124 ]]; then
		TESTS_TIMED_OUT=1
		report_incomplete "skipped: timeout selecting Python environment in $root"
		return 0
	fi
	while IFS= read -r file; do
		[[ -n "$file" ]] && runner+=("$file")
	done <<<"$selection"
	if [[ "${#runner[@]}" -eq 0 ]]; then
		report_incomplete "pytest not found — skipping focused Python tests"
		return 0
	fi
	runner+=(-q --maxfail=1 --tb=short)
	run_pytest_compact "Python tests" "${runner[@]}" "${tests[@]}"
}

run_go_tests() {
	local files=() file
	for file in "$@"; do
		[[ "$file" == *.go ]] && files+=("$file")
	done
	run_project_test_groups go.mod "${files[@]}"
}

run_go_project_tests() {
	local root="$1"
	shift
	[[ "$root" == "." ]] || log_info "Go tests in $root"
	local focus_files=("$@")
	local dirs=()
	local file dir tmp pkg
	for file in "${focus_files[@]}"; do
		[[ "$file" == *.go ]] || continue
		dir=$(dirname "$file")
		[[ "$dir" == "." ]] && dirs+=(".") || dirs+=("./$dir")
	done
	[[ "${#dirs[@]}" -gt 0 ]] || return 0
	command_exists go || {
		report_incomplete "go not found — skipping focused Go tests"
		return 0
	}
	tmp=$(mktemp 2>/dev/null) || {
		log_warn "Temporary file unavailable; checks incomplete"
		return 2
	}
	printf '%s\n' "${dirs[@]}" | unique_lines >"$tmp"
	local status=0
	while IFS= read -r pkg; do
		[[ -n "$pkg" ]] || continue
		run_and_capture "Go tests" go test -json -failfast "$pkg" || status=2
	done <"$tmp"
	rm -f "$tmp"
	return "$status"
}

rust_nearest_manifest() {
	local file="$1" dir
	dir=$(dirname "$file")
	while [[ -n "$dir" && "$dir" != "/" ]]; do
		[[ "$dir" == "." ]] && break
		if [[ -f "$dir/Cargo.toml" ]]; then
			printf '%s\n' "$dir/Cargo.toml"
			return 0
		fi
		dir=$(dirname "$dir")
	done
	[[ -f Cargo.toml ]] && printf '%s\n' "Cargo.toml"
}

run_rust_tests() {
	local focus_files=("$@")
	local manifests=()
	local file manifest tmp status=0
	for file in "${focus_files[@]}"; do
		case "$file" in
		*.rs | Cargo.toml | Cargo.lock | rust-toolchain | rust-toolchain.toml) ;;
		*) continue ;;
		esac
		manifest=$(rust_nearest_manifest "$file" || true)
		[[ -n "$manifest" ]] && manifests+=("$manifest")
	done
	[[ "${#manifests[@]}" -gt 0 ]] || return 0
	command_exists cargo || {
		report_incomplete "cargo not found — skipping focused Rust tests"
		return 0
	}
	tmp=$(mktemp 2>/dev/null) || {
		log_warn "Temporary file unavailable; checks incomplete"
		return 2
	}
	printf '%s\n' "${manifests[@]}" | unique_lines >"$tmp"
	while IFS= read -r manifest; do
		[[ -n "$manifest" ]] || continue
		run_and_capture "Rust tests" cargo test --manifest-path "$manifest" --all-targets || status=2
	done <"$tmp"
	rm -f "$tmp"
	return "$status"
}

csharp_find_containing_solution() {
	local file="$1" dir candidate
	if [[ "$file" == *.sln && -f "$file" ]]; then
		printf '%s\n' "$file"
		return 0
	fi
	dir=$(dirname "$file")
	while [[ -n "$dir" && "$dir" != "/" ]]; do
		candidate=$(find "$dir" -maxdepth 1 -type f -name "*.sln" | sort | head -n 1)
		if [[ -n "$candidate" ]]; then
			printf '%s\n' "${candidate#./}"
			return 0
		fi
		[[ "$dir" == "." ]] && break
		dir=$(dirname "$dir")
	done
	candidate=$(find . -maxdepth 1 -type f -name "*.sln" | sort | head -n 1)
	[[ -n "$candidate" ]] && printf '%s\n' "${candidate#./}"
}

csharp_nearest_csproj() {
	local file="$1" dir candidate
	if [[ "$file" == *.csproj && -f "$file" ]]; then
		printf '%s\n' "$file"
		return 0
	fi
	dir=$(dirname "$file")
	while [[ -n "$dir" && "$dir" != "/" ]]; do
		candidate=$(find "$dir" -maxdepth 1 -type f -name "*.csproj" | sort | head -n 1)
		if [[ -n "$candidate" ]]; then
			printf '%s\n' "${candidate#./}"
			return 0
		fi
		[[ "$dir" == "." ]] && break
		dir=$(dirname "$dir")
	done
	candidate=$(find . -maxdepth 1 -type f -name "*.csproj" | sort | head -n 1)
	[[ -n "$candidate" ]] && printf '%s\n' "${candidate#./}"
}

csharp_is_test_project() {
	local project="$1"
	case "$(basename "$project")" in
	*.Tests.csproj | *.Test.csproj | *Tests*.csproj | *Test*.csproj) return 0 ;;
	esac
	grep -qiE '<IsTestProject>[[:space:]]*true[[:space:]]*</IsTestProject>|Microsoft\.NET\.Test\.Sdk|xunit|nunit|MSTest\.TestFramework' "$project" 2>/dev/null
}

csharp_nearest_test_csproj() {
	local file="$1" dir candidate
	if [[ "$file" == *.csproj ]] && csharp_is_test_project "$file"; then
		printf '%s\n' "$file"
		return 0
	fi
	dir=$(dirname "$file")
	while [[ -n "$dir" && "$dir" != "/" ]]; do
		while IFS= read -r candidate; do
			[[ -n "$candidate" ]] || continue
			if csharp_is_test_project "$candidate"; then
				printf '%s\n' "${candidate#./}"
				return 0
			fi
		done < <(find "$dir" -maxdepth 1 -type f -name "*.csproj" | sort)
		[[ "$dir" == "." ]] && break
		dir=$(dirname "$dir")
	done
	return 1
}

csharp_test_target_for_file() {
	local file="$1" target
	case "$file" in
	*.sln)
		[[ -f "$file" ]] && printf '%s\n' "$file"
		return 0
		;;
	*.csproj)
		if csharp_is_test_project "$file"; then
			printf '%s\n' "$file"
			return 0
		fi
		target=$(csharp_nearest_test_csproj "$file" || true)
		[[ -n "$target" ]] && {
			printf '%s\n' "$target"
			return 0
		}
		target=$(csharp_find_containing_solution "$file" || true)
		[[ -n "$target" ]] && {
			printf '%s\n' "$target"
			return 0
		}
		printf '%s\n' "$file"
		return 0
		;;
	*.cs | *.props | *.targets)
		target=$(csharp_nearest_test_csproj "$file" || true)
		[[ -n "$target" ]] && {
			printf '%s\n' "$target"
			return 0
		}
		target=$(csharp_find_containing_solution "$file" || true)
		[[ -n "$target" ]] && {
			printf '%s\n' "$target"
			return 0
		}
		target=$(csharp_nearest_csproj "$file" || true)
		[[ -n "$target" ]] && {
			printf '%s\n' "$target"
			return 0
		}
		;;
	esac
	return 1
}

run_csharp_tests() {
	local focus_files=("$@")
	local targets=()
	local file target tmp status=0
	for file in "${focus_files[@]}"; do
		case "$file" in
		*.cs | *.csproj | *.sln | *.props | *.targets) ;;
		*) continue ;;
		esac
		target=$(csharp_test_target_for_file "$file" || true)
		[[ -n "$target" ]] && targets+=("$target")
	done
	[[ "${#targets[@]}" -gt 0 ]] || return 0
	command_exists dotnet || {
		report_incomplete "dotnet not found — skipping focused C# tests"
		return 0
	}
	tmp=$(mktemp 2>/dev/null) || {
		log_warn "Temporary file unavailable; checks incomplete"
		return 2
	}
	printf '%s\n' "${targets[@]}" | unique_lines >"$tmp"
	while IFS= read -r target; do
		[[ -n "$target" ]] || continue
		run_and_capture "C# tests" dotnet test "$target" || status=2
	done <"$tmp"
	rm -f "$tmp"
	return "$status"
}

csharp_full_test_target() {
	local candidate
	candidate=$(find . -maxdepth 4 -type f -name "*.sln" | sort | head -n 1)
	if [[ -n "$candidate" ]]; then
		printf '%s\n' "${candidate#./}"
		return 0
	fi
	while IFS= read -r candidate; do
		[[ -n "$candidate" ]] || continue
		if csharp_is_test_project "$candidate"; then
			printf '%s\n' "${candidate#./}"
			return 0
		fi
	done < <(find . -maxdepth 5 -type f -name "*.csproj" | sort)
	candidate=$(find . -maxdepth 5 -type f -name "*.csproj" | sort | head -n 1)
	[[ -n "$candidate" ]] && printf '%s\n' "${candidate#./}"
}

jvm_nearest_gradle_root() {
	local file="$1" dir build_candidate=""
	dir=$(dirname "$file")
	while [[ -n "$dir" && "$dir" != "/" ]]; do
		if [[ -f "$dir/settings.gradle" || -f "$dir/settings.gradle.kts" || -x "$dir/gradlew" ]]; then
			printf '%s\n' "$dir"
			return 0
		fi
		if [[ -z "$build_candidate" ]] && { [[ -f "$dir/build.gradle" ]] || [[ -f "$dir/build.gradle.kts" ]]; }; then
			build_candidate="$dir"
		fi
		[[ "$dir" == "." ]] && break
		dir=$(dirname "$dir")
	done
	if [[ -f settings.gradle || -f settings.gradle.kts || -x gradlew ]]; then
		printf '%s\n' "."
		return 0
	fi
	[[ -n "$build_candidate" ]] && printf '%s\n' "$build_candidate"
}

jvm_nearest_gradle_project_dir() {
	local root="$1" file="$2" dir
	dir=$(dirname "$file")
	while [[ -n "$dir" && "$dir" != "/" ]]; do
		if [[ -f "$dir/build.gradle" || -f "$dir/build.gradle.kts" ]]; then
			printf '%s\n' "$dir"
			return 0
		fi
		[[ "$dir" == "$root" || "$dir" == "." ]] && break
		dir=$(dirname "$dir")
	done
	printf '%s\n' "$root"
}

jvm_gradle_test_task() {
	local root="$1" file="$2" project_dir rel
	project_dir=$(jvm_nearest_gradle_project_dir "$root" "$file")
	if [[ "$project_dir" == "$root" || "$project_dir" == "." ]]; then
		printf '%s\n' "test"
		return 0
	fi
	rel="${project_dir#./}"
	if [[ "$root" != "." ]]; then
		rel="${rel#"$root"/}"
	fi
	printf ':%s:test\n' "${rel//\//:}"
}

jvm_nearest_pom() {
	local file="$1" dir
	if [[ "$file" == pom.xml && -f "$file" ]]; then
		printf '%s\n' "$file"
		return 0
	fi
	dir=$(dirname "$file")
	while [[ -n "$dir" && "$dir" != "/" ]]; do
		if [[ -f "$dir/pom.xml" ]]; then
			printf '%s\n' "$dir/pom.xml"
			return 0
		fi
		[[ "$dir" == "." ]] && break
		dir=$(dirname "$dir")
	done
	[[ -f pom.xml ]] && printf '%s\n' "pom.xml"
}

jvm_test_filter_for_file() {
	local file="$1" base stem
	base=$(basename "$file")
	stem="${base%.*}"
	case "$base" in
	*Test.java | *Tests.java | *Spec.java | *IT.java | *Test.kt | *Tests.kt | *Spec.kt | *IT.kt) printf '%s\n' "$stem" ;;
	esac
}

jvm_find_tests_for_source() {
	local base_dir="$1" file="$2" stem candidate
	stem=$(basename "$file")
	stem="${stem%.*}"
	[[ -d "$base_dir" ]] || base_dir="."
	find "$base_dir" -maxdepth 8 -type f \( \
		-name "${stem}Test.java" -o -name "${stem}Tests.java" -o -name "${stem}Spec.java" -o -name "${stem}IT.java" -o \
		-name "${stem}Test.kt" -o -name "${stem}Tests.kt" -o -name "${stem}Spec.kt" -o -name "${stem}IT.kt" \
		\) 2>/dev/null | while IFS= read -r candidate; do
		jvm_test_filter_for_file "$candidate"
	done
}

jvm_is_build_file() {
	case "$(basename "$1")" in
	pom.xml | build.gradle | build.gradle.kts | settings.gradle | settings.gradle.kts | gradle.properties) return 0 ;;
	*) return 1 ;;
	esac
}

jvm_gradle_available() {
	local root="$1"
	[[ -x "$root/gradlew" ]] || command_exists gradle
}

jvm_maven_available() {
	local pom="$1" dir
	dir=$(dirname "$pom")
	[[ -x "$dir/mvnw" ]] || command_exists mvn
}

jvm_run_gradle_tests() {
	local root="$1" task="$2" filter="${3:-}" old_pwd status
	if [[ -x "$root/gradlew" ]]; then
		old_pwd=$PWD
		cd "$root" || return 0
		if [[ -n "$filter" ]]; then
			run_and_capture "JVM tests (Gradle)" ./gradlew "$task" --tests "$filter"
			status=$?
		else
			run_and_capture "JVM tests (Gradle)" ./gradlew "$task"
			status=$?
		fi
		cd "$old_pwd" || return "$status"
		return "$status"
	elif command_exists gradle; then
		if [[ -n "$filter" ]]; then
			run_and_capture "JVM tests (Gradle)" gradle -p "$root" "$task" --tests "$filter"
		else
			run_and_capture "JVM tests (Gradle)" gradle -p "$root" "$task"
		fi
	else
		report_incomplete "gradle not found — skipping focused JVM Gradle tests"
		return 0
	fi
}

jvm_run_maven_tests() {
	local pom="$1" filter="${2:-}" dir old_pwd status
	dir=$(dirname "$pom")
	if [[ -x "$dir/mvnw" ]]; then
		old_pwd=$PWD
		cd "$dir" || return 0
		if [[ -n "$filter" ]]; then
			run_and_capture "JVM tests (Maven)" ./mvnw -q "-Dtest=$filter" test
			status=$?
		else
			run_and_capture "JVM tests (Maven)" ./mvnw -q test
			status=$?
		fi
		cd "$old_pwd" || return "$status"
		return "$status"
	elif command_exists mvn; then
		if [[ -n "$filter" ]]; then
			run_and_capture "JVM tests (Maven)" mvn -q -f "$pom" "-Dtest=$filter" test
		else
			run_and_capture "JVM tests (Maven)" mvn -q -f "$pom" test
		fi
	else
		report_incomplete "mvn not found — skipping focused JVM Maven tests"
		return 0
	fi
}

run_jvm_tests() {
	local focus_files=("$@")
	local tmp file root project_dir task filter pom status=0
	tmp=$(mktemp 2>/dev/null) || {
		log_warn "Temporary file unavailable; checks incomplete"
		return 2
	}
	for file in "${focus_files[@]}"; do
		case "$file" in
		*.java | *.kt | *.kts | pom.xml | build.gradle | settings.gradle | gradle.properties) ;;
		*) continue ;;
		esac
		root=$(jvm_nearest_gradle_root "$file" || true)
		if [[ -n "$root" ]] && jvm_gradle_available "$root"; then
			task=$(jvm_gradle_test_task "$root" "$file")
			project_dir=$(jvm_nearest_gradle_project_dir "$root" "$file")
			filter=$(jvm_test_filter_for_file "$file" || true)
			if [[ -z "$filter" ]] && ! jvm_is_build_file "$file"; then
				filter=$(jvm_find_tests_for_source "$project_dir" "$file" | head -n 1)
			fi
			printf 'g|%s|%s|%s\n' "$root" "$task" "$filter"
			continue
		fi
		pom=$(jvm_nearest_pom "$file" || true)
		if [[ -n "$pom" ]] && jvm_maven_available "$pom"; then
			filter=$(jvm_test_filter_for_file "$file" || true)
			if [[ -z "$filter" ]] && ! jvm_is_build_file "$file"; then
				filter=$(jvm_find_tests_for_source "$(dirname "$pom")" "$file" | head -n 1)
			fi
			printf 'm|%s|test|%s\n' "$pom" "$filter"
		fi
	done | sort -u >"$tmp"
	while IFS='|' read -r kind target task filter; do
		[[ -n "$kind" && -n "$target" ]] || continue
		case "$kind" in
		g) jvm_run_gradle_tests "$target" "$task" "$filter" || status=2 ;;
		m) jvm_run_maven_tests "$target" "$filter" || status=2 ;;
		esac
	done <"$tmp"
	rm -f "$tmp"
	return "$status"
}

run_full_jvm_tests() {
	local root pom
	root=$(find . -maxdepth 3 \( -name settings.gradle -o -name settings.gradle.kts -o -name gradlew -o -name build.gradle -o -name build.gradle.kts \) -print 2>/dev/null | sort | head -n 1)
	if [[ -n "$root" ]]; then
		root=$(dirname "$root")
		if jvm_gradle_available "$root"; then
			jvm_run_gradle_tests "$root" test
			return $?
		fi
		report_incomplete "gradle not found — skipping full JVM Gradle tests"
	fi
	pom=$(find . -maxdepth 4 -type f -name pom.xml | sort | head -n 1)
	if [[ -n "$pom" ]]; then
		if jvm_maven_available "$pom"; then
			jvm_run_maven_tests "$pom"
			return $?
		fi
		report_incomplete "mvn not found — skipping full JVM Maven tests"
	fi
	return 1
}

is_js_test_file() {
	local base
	base=$(basename "$1")
	case "$base" in
	*.test.js | *.test.jsx | *.test.ts | *.test.tsx | *.test.mjs | *.test.cjs | *.test.mts | *.test.cts | \
		*.spec.js | *.spec.jsx | *.spec.ts | *.spec.tsx | *.spec.mjs | *.spec.cjs | *.spec.mts | *.spec.cts | \
		test_*.js | test_*.jsx | test_*.ts | test_*.tsx | test_*.mjs | test_*.cjs | test_*.mts | test_*.cts | \
		*_test.js | *_test.jsx | *_test.ts | *_test.tsx | *_test.mjs | *_test.cjs | *_test.mts | *_test.cts) return 0 ;;
	esac
	case "$1" in
	*/__tests__/* | */tests/* | tests/* | */test/* | test/*) return 0 ;;
	*) return 1 ;;
	esac
}

js_file_has_tests() {
	grep -Eq '(^|[^[:alnum:]_$])(describe|it|test|suite)([[:space:]]*\.[[:space:]]*[[:alpha:]_$][[:alnum:]_$]*)*[[:space:]]*\(' "$1" 2>/dev/null
}

find_js_tests_for_source() {
	local file="$1" stem="${1##*/}" candidate base dir candidate_dir owner candidate_owner relative
	stem=${stem%.*}
	dir=${file%/*}
	[[ "$dir" == "$file" ]] && dir=.
	owner=$(nearest_project_root "$file" package.json)
	shift
	for candidate in "$@"; do
		candidate_owner=$(nearest_project_root "$candidate" package.json)
		[[ "$candidate_owner" == "$owner" ]] || continue
		relative="$candidate"
		[[ "$owner" == "." ]] || relative=${candidate#"$owner/"}
		candidate_dir=${candidate%/*}
		case "$relative" in tests/* | test/* | src/*) ;; *) [[ "$candidate_dir" == "$dir" ]] || continue ;; esac
		base=${candidate##*/}
		if [[ "$base" == "$stem".test.* || "$base" == "$stem".spec.* || "$base" == test_"$stem".* ]]; then
			printf '%s\n' "$candidate"
		fi
	done
}

index_js_test_candidates() {
	local test_dir file dir root
	local search_dirs=(tests test src)
	while IFS= read -r root; do
		[[ "$root" == "." ]] || search_dirs+=("$root/tests" "$root/test" "$root/src")
	done < <(for file in "$@"; do nearest_project_root "$file" package.json; done | sort -u)
	for test_dir in "${search_dirs[@]}"; do
		[[ -d "$test_dir" ]] || continue
		find "$test_dir" -type d ! -path "$test_dir" -exec test -f '{}/package.json' \; -prune -o \
			-type f \( -name '*.test.*' -o -name '*.spec.*' -o -name 'test_*.*' \) -print 2>/dev/null
	done
	# Adjacent tests outside the recursively indexed roots need one scan per dir.
	while IFS= read -r dir; do
		find "$dir" -maxdepth 1 -type f \( -name '*.test.*' -o -name '*.spec.*' -o -name 'test_*.*' \) 2>/dev/null
	done < <(
		for file in "$@"; do
			if [[ "$file" == tests/* || "$file" == test/* || "$file" == src/* ]]; then continue; fi
			dir=${file%/*}
			[[ "$dir" == "$file" ]] && dir=.
			printf '%s\n' "$dir"
		done | sort -u
	)
}

js_runner_command() {
	local bin has_test_config=0
	if find . -maxdepth 3 -type d ! -path . -exec test -f '{}/package.json' \; -prune -o -name 'vitest.config.*' -print -quit 2>/dev/null | grep -q .; then
		has_test_config=1
		bin=$(resolve_node_tool vitest || true)
		if [[ -n "$bin" ]]; then
			printf 'vitest|%s\n' "$bin"
			return 0
		fi
	fi
	if find . -maxdepth 3 -type d ! -path . -exec test -f '{}/package.json' \; -prune -o -name 'jest.config.*' -print -quit 2>/dev/null | grep -q .; then
		has_test_config=1
		bin=$(resolve_node_tool jest || true)
		if [[ -n "$bin" ]]; then
			printf 'jest|%s\n' "$bin"
			return 0
		fi
	fi
	[[ "$has_test_config" -eq 1 ]] && return 1
	if command_exists bun && { [[ -f bun.lockb ]] || [[ -f bun.lock ]]; }; then
		printf '%s\n' "bun|bun"
		return 0
	fi
	return 2
}

js_effective_project_root() {
	local file="$1" root runner code
	root=$(nearest_project_root "$file" package.json)
	while :; do
		runner=$(cd "$root" && js_runner_command)
		code=$?
		if [[ -n "$runner" || "$code" -eq 1 || "$root" == "." ]]; then
			printf '%s\n' "$root"
			return 0
		fi
		root=$(dirname "$root")
	done
}

run_javascript_tests() {
	local files=() file
	for file in "$@"; do
		case "$file" in
		*.js | *.jsx | *.ts | *.tsx | *.mjs | *.cjs | *.mts | *.cts) files+=("$file") ;;
		esac
	done
	run_project_test_groups package.json "${files[@]}"
}

run_javascript_project_tests() {
	local root="$1"
	shift
	[[ "$root" == "." ]] || log_info "JS tests in $root"
	local focus_files=("$@")
	local tests=()
	local mapped_tests=()
	local sources=()
	local deduped=()
	local file tmp runner kind bin candidate status
	for file in "${focus_files[@]}"; do
		case "$file" in
		*.js | *.jsx | *.ts | *.tsx | *.mjs | *.cjs | *.mts | *.cts) ;;
		*) continue ;;
		esac
		if is_js_test_file "$file" && js_file_has_tests "$file"; then
			tests+=("$file")
		else
			sources+=("$file")
		fi
	done
	[[ "${#sources[@]}" -gt 0 || "${#tests[@]}" -gt 0 || "${#mapped_tests[@]}" -gt 0 ]] || return 0

	runner=$(js_runner_command || true)
	if [[ -z "$runner" ]]; then
		report_incomplete "No focused JS test runner found — skipping JS tests"
		return 0
	fi

	if [[ "$runner" == bun\|* && "${#sources[@]}" -gt 0 ]]; then
		local candidates=()
		while IFS= read -r candidate; do candidates+=("$candidate"); done < <(index_js_test_candidates "${sources[@]}")
		for file in "${sources[@]}"; do
			while IFS= read -r candidate; do mapped_tests+=("$candidate"); done < <(find_js_tests_for_source "$file" "${candidates[@]}")
		done
	fi

	tmp=$(mktemp 2>/dev/null) || {
		log_warn "Temporary file unavailable; checks incomplete"
		return 2
	}
	printf '%s\n' "${sources[@]}" | unique_lines >"$tmp.sources"
	printf '%s\n' "${tests[@]}" | unique_lines >"$tmp.tests"
	printf '%s\n' "${mapped_tests[@]}" | unique_lines >"$tmp.mapped"
	sources=()
	tests=()
	mapped_tests=()
	while IFS= read -r file; do sources+=("$file"); done <"$tmp.sources"
	while IFS= read -r file; do tests+=("$file"); done <"$tmp.tests"
	while IFS= read -r file; do mapped_tests+=("$file"); done <"$tmp.mapped"
	rm -f "$tmp" "$tmp.sources" "$tmp.tests" "$tmp.mapped"

	kind=${runner%%|*}
	bin=${runner#*|}
	status=0
	case "$kind" in
	vitest)
		if [[ "${#sources[@]}" -gt 0 ]]; then
			run_js_reported_tests "JS related tests (vitest)" vitest "$bin" related "${sources[@]}" --run --passWithNoTests || status=2
		fi
		if [[ "${#tests[@]}" -gt 0 ]]; then
			run_js_reported_tests "JS tests (vitest)" vitest "$bin" run "${tests[@]}" --passWithNoTests || status=2
		fi
		;;
	jest)
		if [[ "${#sources[@]}" -gt 0 ]]; then
			run_js_reported_tests "JS related tests (jest)" jest "$bin" --findRelatedTests "${sources[@]}" --passWithNoTests || status=2
		fi
		if [[ "${#tests[@]}" -gt 0 ]]; then
			run_js_reported_tests "JS tests (jest)" jest "$bin" "${tests[@]}" --passWithNoTests || status=2
		fi
		;;
	bun)
		tests+=("${mapped_tests[@]}")
		[[ "${#tests[@]}" -gt 0 ]] || return 0
		while IFS= read -r file; do deduped+=("$file"); done < <(printf '%s\n' "${tests[@]}" | unique_lines)
		tests=("${deduped[@]}")
		run_js_reported_tests "JS tests (bun)" bun bun test --isolate "${tests[@]}" || status=2
		;;
	esac
	return "$status"
}

find_shell_tests_for_source() {
	local file="$1" base
	base=$(basename "$file")
	base=${base%.*}
	for test_dir in tests test; do
		[[ -d "$test_dir" ]] || continue
		find "$test_dir" -type f \( -name "test_${base}.bats" -o -name "${base}_test.bats" \) 2>/dev/null
	done
}

run_full_javascript_tests() {
	local runner kind bin
	runner=$(js_runner_command || true)
	[[ -n "$runner" ]] || return 1
	kind=${runner%%|*}
	bin=${runner#*|}
	case "$kind" in
	vitest) run_js_reported_tests "vitest" vitest "$bin" run --passWithNoTests ;;
	jest) run_js_reported_tests "jest" jest "$bin" --passWithNoTests ;;
	bun) run_js_reported_tests "bun test" bun bun test --isolate ;;
	*) return 1 ;;
	esac
}

run_shell_tests() {
	local focus_files=("$@")
	local tests=()
	local file tmp
	for file in "${focus_files[@]}"; do
		case "$file" in
		*.bats) tests+=("$file") ;;
		*.sh | *.bash)
			while IFS= read -r candidate; do
				[[ -n "$candidate" ]] && tests+=("$candidate")
			done < <(find_shell_tests_for_source "$file")
			;;
		esac
	done
	[[ "${#tests[@]}" -gt 0 ]] || return 0
	command_exists bats || {
		report_incomplete "bats not found — skipping focused shell tests"
		return 0
	}
	tmp=$(mktemp 2>/dev/null) || {
		log_warn "Temporary file unavailable; checks incomplete"
		return 2
	}
	printf '%s\n' "${tests[@]}" | unique_lines >"$tmp"
	tests=()
	while IFS= read -r file; do tests+=("$file"); done <"$tmp"
	rm -f "$tmp"
	run_and_capture "Shell tests" bats "${tests[@]}"
}

run_full_shell_tests() {
	local tests=()
	local test_dir file tmp
	for test_dir in tests test; do
		[[ -d "$test_dir" ]] || continue
		while IFS= read -r file; do
			[[ -n "$file" ]] && tests+=("$file")
		done < <(find "$test_dir" -type f -name "*.bats" 2>/dev/null)
	done
	[[ "${#tests[@]}" -gt 0 ]] || return 1
	command_exists bats || {
		report_incomplete "bats not found — skipping full shell tests"
		return 0
	}
	tmp=$(mktemp 2>/dev/null) || {
		log_warn "Temporary file unavailable; checks incomplete"
		return 2
	}
	printf '%s\n' "${tests[@]}" | unique_lines >"$tmp"
	tests=()
	while IFS= read -r file; do tests+=("$file"); done <"$tmp"
	rm -f "$tmp"
	run_and_capture "Shell tests" bats "${tests[@]}"
}

run_full_override() {
	local -x UV_NO_SYNC=1
	log_warn "TEST_RUNNER_FULL=1 set — running project-level tests"
	local full_status
	if [[ -f "Makefile" ]]; then
		local target
		for target in test tests check verify; do
			if grep -qE "^[[:space:]]*${target}[[:space:]]*:" Makefile 2>/dev/null; then
				run_and_capture "make $target" make "$target"
				return $?
			fi
		done
	fi
	if [[ -f go.mod ]] && command_exists go; then
		run_and_capture "go test" go test -json -failfast ./...
		return $?
	fi
	if [[ -f Cargo.toml ]]; then
		if command_exists cargo; then
			run_and_capture "cargo test" cargo test --all-targets
			return $?
		fi
		report_incomplete "cargo not found — skipping full Rust tests"
	fi
	run_full_jvm_tests
	full_status=$?
	case "$full_status" in
	0 | 2) return "$full_status" ;;
	esac
	local csharp_target
	csharp_target=$(csharp_full_test_target || true)
	if [[ -n "$csharp_target" ]]; then
		if command_exists dotnet; then
			run_and_capture "dotnet test" dotnet test "$csharp_target"
			return $?
		fi
		report_incomplete "dotnet not found — skipping full C# tests"
	fi
	local pytest_runner=() pytest_arg selection selection_code
	selection=$(pytest_runner_command)
	selection_code=$?
	if [[ "$selection_code" -eq 124 ]]; then
		TESTS_TIMED_OUT=1
		report_incomplete "skipped: timeout selecting Python environment"
		return 0
	fi
	while IFS= read -r pytest_arg; do
		[[ -n "$pytest_arg" ]] && pytest_runner+=("$pytest_arg")
	done <<<"$selection"
	if [[ "${#pytest_runner[@]}" -gt 0 ]]; then
		pytest_runner+=(-q --maxfail=1 --tb=short)
		run_pytest_compact "pytest" "${pytest_runner[@]}"
		return $?
	fi
	if [[ -f package.json ]]; then
		local script
		for script in test tests check verify; do
			package_json_has_script "$script" || continue
			run_package_test_script "$script"
			return $?
		done
	fi
	run_full_javascript_tests
	full_status=$?
	case "$full_status" in
	0 | 2) return "$full_status" ;;
	esac
	run_full_shell_tests
	full_status=$?
	case "$full_status" in
	0 | 2) return "$full_status" ;;
	esac
	report_incomplete "No full project test runner found"
	return 0
}

main() {
	if ! init_hook_input; then finish_hook; fi
	normalize_timeout
	if ! maybe_cd_to_hook_cwd; then finish_hook; fi
	RUN_TREE_FINGERPRINT=$(tree_fingerprint)
	RUN_ATTEMPT_FINGERPRINT=$(attempt_fingerprint)
	log_debug "TEST_RUNNER_TIMEOUT_SECS=$TEST_RUNNER_TIMEOUT_SECS"

	if [[ "${SKIP_TESTS:-}" == "1" ]] || [[ -f ".notests" ]]; then
		echo -e "${CYAN}⏭ Tests skipped${NC}" >&2
		# An explicit skip is not verification; leave pending work intact.
		finish_hook 0
	fi

	if [[ "$TEST_RUNNER_FULL" == "1" ]]; then
		echo "" >&2
		echo "🧪 Running focused tests..." >&2
		echo "─────────────────────────" >&2
		run_full_override
		status=$?
		if [[ "$status" -eq 0 && "$TESTS_TIMED_OUT" -eq 0 && "$TESTS_INCOMPLETE" -eq 0 ]]; then
			clear_hook_state
		else
			record_incomplete_attempt
		fi
		finish_hook "$status"
	fi

	if previous_attempt_matches; then
		log_debug "skipped: unchanged since previous incomplete or failed attempt; retry the reported command explicitly"
		finish_hook
	fi
	local focus_files=()
	local file selection
	if ! selection=$(collect_focus_files); then
		report_incomplete "Could not discover focused tests; agent may continue"
		record_incomplete_attempt
		finish_hook
	fi
	while IFS= read -r file; do
		[[ -n "$file" ]] && focus_files+=("$file")
	done <<<"$selection"

	if [[ "${#focus_files[@]}" -eq 0 ]]; then
		log_debug "skipped: no changed code files with focused test support"
		clear_hook_state
		finish_hook 0
	fi

	echo "" >&2
	echo "🧪 Running focused tests..." >&2
	echo "─────────────────────────" >&2
	log_debug "Focus files: ${focus_files[*]}"
	local status=0
	run_nearest_makefile_tests "${focus_files[@]}" || status=2

	local uncovered_files=() is_covered cf
	for file in "${focus_files[@]}"; do
		is_covered=0
		for cf in "${MAKEFILE_COVERED_FILES[@]}"; do
			[[ "$cf" == "$file" ]] && {
				is_covered=1
				break
			}
		done
		[[ "$is_covered" -eq 1 ]] || uncovered_files+=("$file")
	done

	if [[ "${#uncovered_files[@]}" -gt 0 ]]; then
		run_python_tests "${uncovered_files[@]}" || status=2
		run_go_tests "${uncovered_files[@]}" || status=2
		run_rust_tests "${uncovered_files[@]}" || status=2
		run_jvm_tests "${uncovered_files[@]}" || status=2
		run_csharp_tests "${uncovered_files[@]}" || status=2
		run_javascript_tests "${uncovered_files[@]}" || status=2
		run_shell_tests "${uncovered_files[@]}" || status=2
	fi
	if [[ "$status" -eq 0 && "$TESTS_RAN" -eq 0 ]]; then
		run_package_test_fallback || status=2
	fi

	echo "" >&2
	if [[ "$status" -eq 0 ]]; then
		if [[ "$TESTS_RAN" -eq 0 ]]; then
			TESTS_INCOMPLETE=1
			log_info "unsupported: no targeted tests ran; project fallback requires HOOK_PROJECT_FALLBACK=1"
		elif [[ "$TESTS_PASSED" -eq 0 && "$TESTS_COMMANDS_COMPLETED" -eq 0 ]]; then
			log_info "skipped: no tests completed"
		elif [[ "$TESTS_INCOMPLETE" -eq 1 || "$TESTS_TIMED_OUT" -eq 1 ]]; then
			log_warn "Focused tests incomplete; not all selected checks completed"
		else
			echo -e "${GREEN}✅ Focused tests passed${NC}" >&2
		fi
		if [[ "$TESTS_TIMED_OUT" -eq 0 && "$TESTS_INCOMPLETE" -eq 0 ]]; then
			clear_hook_state
		else
			record_incomplete_attempt
			log_debug "keeping pending state: checks are incomplete"
		fi
	else
		echo -e "${RED}❌ Focused test command failed (advisory; agent may continue)${NC}" >&2
		record_incomplete_attempt
	fi
	finish_hook "$status"
}

trap 'unexpected_hook_exit "$?"' EXIT
HOOK_SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
main "$@"
