#!/usr/bin/env bash
# Shared utilities for smart-lint modules: colors, logging, error collection, formatters.

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'
CLAUDE_HOOKS_DEBUG="${CLAUDE_HOOKS_DEBUG:-0}"
PROJECT_TYPE="${PROJECT_TYPE:-unknown}"
SMART_LINT_DIFF_FALLBACK_LIMIT="${SMART_LINT_DIFF_FALLBACK_LIMIT:-5}"
SMART_LINT_COMPACT_LINES=80
HOOK_PROJECT_FALLBACK="${HOOK_PROJECT_FALLBACK:-1}"
SMART_LINT_FORMAT_RAN=0
SMART_LINT_LINT_RAN=0
HOOK_INPUT_JSON="${HOOK_INPUT_JSON:-}"
HOOK_EDITED_FILES_LOADED=0
HOOK_EDITED_FILES=()

log_debug() { [[ "$CLAUDE_HOOKS_DEBUG" == "1" ]] && echo -e "${CYAN}[DEBUG]${NC} $*" >&2; }
log_info() { echo -e "${BLUE}[INFO]${NC} $*" >&2; }
command_exists() { command -v "$1" &>/dev/null; }
mark_format_ran() { SMART_LINT_FORMAT_RAN=1; }
mark_lint_ran() { SMART_LINT_LINT_RAN=1; }
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
}

declare -a ERRORS=()
add_error() {
	ERRORS+=("${RED}❌ $1${NC}\n$2")
}

print_summary_and_exit() {
	if [ ${#ERRORS[@]} -gt 0 ]; then
		echo -e "${RED}❌ ${#ERRORS[@]} blocking issue(s):${NC}" >&2
		for err in "${ERRORS[@]}"; do
			echo -e "$err" >&2
		done
		# Exit code 2 = blocking error in Claude Code hooks
		# Sends stderr to Claude for automatic processing and fixing
		# See: https://docs.claude.com/en/docs/claude-code/hooks
		exit 2
	else
		local total_words=0
		local w
		# CLAUDE.md + settings
		for f in ~/.claude/CLAUDE.md ~/.claude/settings.json; do
			[[ -f "$f" ]] && {
				w=$(wc -w <"$f" 2>/dev/null | tr -d ' ')
				total_words=$((total_words + w))
			}
		done
		# Commands, skills, agents
		shopt -s globstar 2>/dev/null
		for f in ~/.claude/commands/**/*.md \
			~/.claude/skills/*/SKILL.md ~/.claude/agents/**/*.md; do
			[[ -f "$f" ]] && {
				w=$(wc -w <"$f" 2>/dev/null | tr -d ' ')
				total_words=$((total_words + w))
			}
		done
		local approx_tokens=$((total_words * 4 / 3))
		echo -e "${PROJECT_TYPE} project ${GREEN}✅ Style OK${NC} ${CYAN}📊 ~${approx_tokens} tokens${NC}" >&2
		exit 0
	fi
}

_extract_hook_files_python() {
	command_exists python3 || return 0
	python3 -c '
import json
import os
import re
import sys
from pathlib import Path

try:
    data = json.loads(sys.stdin.read() or "{}")
except Exception:
    sys.exit(0)
if not isinstance(data, dict):
    sys.exit(0)

cwd = Path(str(data.get("cwd") or os.getcwd())).resolve()
seen = set()
out = []


def add(raw):
    if not isinstance(raw, str):
        return
    value = raw.strip()
    if not value or "\x00" in value or value == "/dev/null":
        return
    if value.startswith(("a/", "b/")):
        value = value[2:]
    p = Path(value)
    try:
        if p.is_absolute():
            full = p.resolve()
            try:
                rel = full.relative_to(cwd)
            except ValueError:
                return
        else:
            rel = p
            if ".." in rel.parts:
                return
            full = (cwd / rel).resolve()
            try:
                rel = full.relative_to(cwd)
            except ValueError:
                return
    except Exception:
        return
    if not full.is_file():
        return
    text = rel.as_posix()
    if text not in seen:
        seen.add(text)
        out.append(text)


def scan_patch(text):
    if not isinstance(text, str):
        return
    if "*** " not in text and "diff --git" not in text and "+++ " not in text:
        return
    patterns = [
        r"^\*\*\* (?:Update|Add|Delete) File: (.+)$",
        r"^\+\+\+ b/(.+)$",
        r"^--- a/(.+)$",
        r"^diff --git a/(.+?) b/.+$",
    ]
    for line in text.splitlines():
        for pattern in patterns:
            match = re.match(pattern, line)
            if match:
                add(match.group(1))


def walk(obj):
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in {"file_path", "path", "filename", "source_file", "target_file"}:
                add(value)
            elif key in {"patch", "diff"}:
                scan_patch(value)
            walk(value)
    elif isinstance(obj, list):
        for item in obj:
            walk(item)
    elif isinstance(obj, str):
        scan_patch(obj)

walk(data.get("tool_input", data))
for path in out:
    print(path)
' <<<"$HOOK_INPUT_JSON"
}

_extract_hook_files_jq() {
	command_exists jq || return 0
	jq -r '(.tool_input // .) | .. | objects | (.file_path? // .path? // .filename? // empty)' <<<"$HOOK_INPUT_JSON" 2>/dev/null | while IFS= read -r file; do
		[[ -n "$file" && -f "$file" ]] && printf '%s\n' "$file"
	done
}

_extract_hook_files() {
	if command_exists python3; then
		_extract_hook_files_python
	else
		_extract_hook_files_jq
	fi
}

_hook_session_id() {
	if [[ -n "$HOOK_INPUT_JSON" ]] && command_exists python3; then
		local parsed
		parsed=$(python3 -c 'import json,sys
try:
    data=json.loads(sys.stdin.read() or "{}")
except Exception:
    data={}
print(str(data.get("session_id") or "default"))
' <<<"$HOOK_INPUT_JSON" 2>/dev/null || true)
		[[ -n "$parsed" ]] && printf '%s\n' "$parsed" && return 0
	fi
	printf '%s\n' "default"
}

_hook_state_path() {
	git rev-parse --git-dir >/dev/null 2>&1 || return 1
	local session_id safe_session_id
	session_id=$(_hook_session_id)
	safe_session_id=$(printf '%s' "$session_id" | tr -c 'A-Za-z0-9_.-' '_')
	git rev-parse --git-path "cc-thingz/hook-files-${safe_session_id:-default}" 2>/dev/null
}

load_hook_edited_files() {
	[[ "$HOOK_EDITED_FILES_LOADED" -eq 1 ]] && return 0
	HOOK_EDITED_FILES_LOADED=1
	HOOK_EDITED_FILES=()
	[[ -n "$HOOK_INPUT_JSON" ]] || return 0

	local file
	while IFS= read -r file; do
		[[ -n "$file" ]] && HOOK_EDITED_FILES+=("$file")
	done < <(_extract_hook_files | sort -u)
	log_debug "Hook-scoped files: ${HOOK_EDITED_FILES[*]}"
}

record_hook_edited_files() {
	load_hook_edited_files
	[[ "${#HOOK_EDITED_FILES[@]}" -gt 0 ]] || return 0

	local state_path state_dir tmp
	state_path=$(_hook_state_path) || return 0
	state_dir=$(dirname "$state_path")
	mkdir -p "$state_dir" 2>/dev/null || return 0
	tmp="${state_path}.$$"
	{
		[[ -f "$state_path" ]] && cat "$state_path"
		printf '%s\n' "${HOOK_EDITED_FILES[@]}"
	} | sort -u >"$tmp" 2>/dev/null && mv "$tmp" "$state_path"
	rm -f "$tmp"
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
	local ext
	for ext in "$@"; do
		if [[ "$file" == *"$ext" ]]; then
			return 0
		fi
	done
	return 1
}

_diff_fallback_files() {
	if ! git rev-parse --git-dir >/dev/null 2>&1; then
		return
	fi
	{
		git diff --name-only --diff-filter=ACMRTUXB --cached HEAD 2>/dev/null || true
		git diff --name-only --diff-filter=ACMRTUXB 2>/dev/null || true
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
	local max_lines="$SMART_LINT_COMPACT_LINES"
	awk -v max="$max_lines" '
		/^[[:space:]]*$/ { next }
		{ lines[++count] = $0 }
		END {
			limit = count < max ? count : max
			for (i = 1; i <= limit; i++) print lines[i]
			if (count > max) printf("... truncated %d line(s) ...\n", count - max)
		}
	' <<<"$1"
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

	if ! output=$($format_cmd "${files[@]}" 2>&1); then
		add_error "$name failed" "$(compact_output "$output")"
		return 2
	fi

	if [[ "$mode" == "format-only" || -z "$check_cmd" ]]; then
		return 0
	fi

	if output=$($check_cmd "${files[@]}" 2>&1); then
		return 0
	else
		add_error "$name needs fixing" "$(compact_output "$output")"
	fi
}

run_command_compact() {
	local name="$1"
	shift
	if output=$("$@" 2>&1); then
		log_debug "$name passed."
		return 0
	else
		add_error "$name found issues" "$(compact_output "$output")"
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
	run_package_lint_fallback
	run_make_lint_fallback
}
