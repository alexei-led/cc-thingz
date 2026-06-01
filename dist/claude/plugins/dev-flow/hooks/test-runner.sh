#!/usr/bin/env bash
# test-runner.sh - Focused test execution at agent-finish time.
#
# Runs tests causally related to edited files. Never runs a full project test
# suite unless TEST_RUNNER_FULL=1 is set explicitly.

set +e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

HOOK_INPUT_JSON="${HOOK_INPUT_JSON:-}"
TEST_RUNNER_DIFF_FALLBACK_LIMIT="${TEST_RUNNER_DIFF_FALLBACK_LIMIT:-50}"
TEST_RUNNER_FULL="${TEST_RUNNER_FULL:-0}"
TEST_RUNNER_DEBUG="${TEST_RUNNER_DEBUG:-0}"
TEST_RUNNER_COMPACT_LINES=120
HOOK_PROJECT_FALLBACK="${HOOK_PROJECT_FALLBACK:-0}"
TESTS_RAN=0

log_debug() { [[ "$TEST_RUNNER_DEBUG" == "1" ]] && echo -e "${CYAN}[DEBUG]${NC} $*" >&2; }
log_info() { echo -e "${BLUE}[INFO]${NC} $*" >&2; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $*" >&2; }
command_exists() { command -v "$1" &>/dev/null; }
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
		HOOK_INPUT_JSON=$(cat 2>/dev/null || true)
	fi
}

json_field() {
	local field="$1"
	[[ -n "$HOOK_INPUT_JSON" ]] || return 1
	command_exists python3 || return 1
	python3 -c 'import json,sys
field=sys.argv[1]
try:
    data=json.loads(sys.stdin.read() or "{}")
except Exception:
    sys.exit(1)
value=data.get(field) if isinstance(data, dict) else None
if value is None:
    sys.exit(1)
print(str(value))
' "$field" <<<"$HOOK_INPUT_JSON" 2>/dev/null
}

maybe_cd_to_hook_cwd() {
	local hook_cwd
	hook_cwd=$(json_field cwd || true)
	if [[ -n "$hook_cwd" && -d "$hook_cwd" ]]; then
		cd "$hook_cwd" || return 0
	fi
}

hook_session_id() {
	local sid
	sid=$(json_field session_id || true)
	[[ -n "$sid" ]] && printf '%s\n' "$sid" || printf '%s\n' default
}

hook_state_path() {
	git rev-parse --git-dir >/dev/null 2>&1 || return 1
	local session_id safe_session_id
	session_id=$(hook_session_id)
	safe_session_id=$(printf '%s' "$session_id" | tr -c 'A-Za-z0-9_.-' '_')
	git rev-parse --git-path "cc-thingz/hook-files-${safe_session_id:-default}" 2>/dev/null
}

clear_hook_state() {
	local state_path
	state_path=$(hook_state_path 2>/dev/null || true)
	[[ -n "$state_path" ]] && rm -f "$state_path"
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
	*.py | *.go | *.js | *.jsx | *.ts | *.tsx | *.mjs | *.cjs | *.mts | *.cts | *.sh | *.bash | *.bats) return 0 ;;
	*) return 1 ;;
	esac
}

diff_fallback_files() {
	git rev-parse --git-dir >/dev/null 2>&1 || return 0
	{
		git diff --name-only --diff-filter=ACMRTUXB --cached HEAD 2>/dev/null || true
		git diff --name-only --diff-filter=ACMRTUXB 2>/dev/null || true
		git ls-files --others --exclude-standard 2>/dev/null || true
	} | sort -u
}

collect_focus_files() {
	local state_path file count source="session state"
	local tmp_raw tmp_filtered
	state_path=$(hook_state_path 2>/dev/null || true)
	tmp_raw=$(mktemp 2>/dev/null || printf '/tmp/cc-thingz-focus-raw.%s' "$$")
	tmp_filtered=$(mktemp 2>/dev/null || printf '/tmp/cc-thingz-focus-filtered.%s' "$$")
	if [[ -n "$state_path" && -s "$state_path" ]]; then
		cat "$state_path" >"$tmp_raw"
	else
		source="git diff fallback"
		diff_fallback_files >"$tmp_raw"
	fi
	while IFS= read -r file; do
		[[ -n "$file" && -f "$file" ]] || continue
		path_is_excluded "$file" && continue
		has_code_extension "$file" || continue
		printf '%s\n' "$file"
	done <"$tmp_raw" | sort -u >"$tmp_filtered"
	count=$(wc -l <"$tmp_filtered" 2>/dev/null | tr -d ' ')
	if [[ "$source" == "git diff fallback" && "$count" -gt "$TEST_RUNNER_DIFF_FALLBACK_LIMIT" ]]; then
		log_warn "Skipping focused tests: diff fallback exceeded TEST_RUNNER_DIFF_FALLBACK_LIMIT=$TEST_RUNNER_DIFF_FALLBACK_LIMIT"
		rm -f "$tmp_raw" "$tmp_filtered"
		return 0
	fi
	cat "$tmp_filtered"
	rm -f "$tmp_raw" "$tmp_filtered"
	log_debug "Focus-file source: $source"
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
	yarn) run_test_compact "yarn $script" "$bin" run "$script" ;;
	bun) run_test_compact "bun $script" "$bin" run "$script" ;;
	npm) run_test_compact "npm $script" "$bin" run --silent "$script" ;;
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

compact_output() {
	local max_lines="$TEST_RUNNER_COMPACT_LINES"
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

run_test_compact() {
	local label="$1"
	shift
	TESTS_RAN=1
	log_info "Running: $*"
	local output code
	output=$("$@" 2>&1)
	code=$?
	if [[ "$code" -eq 0 ]]; then
		log_debug "$label passed"
		return 0
	fi
	[[ -n "$output" ]] && compact_output "$output" >&2
	log_warn "$label failed with exit $code"
	return 2
}

run_and_capture() {
	run_test_compact "$@"
}

# Like run_test_compact, but treats pytest exit code 5 ("no tests collected")
# as success — handing pytest a file with no test functions is not a failure.
run_pytest_compact() {
	local label="$1"
	shift
	TESTS_RAN=1
	log_info "Running: $*"
	local output code
	output=$("$@" 2>&1)
	code=$?
	if [[ "$code" -eq 0 || "$code" -eq 5 ]]; then
		log_debug "$label passed (exit $code)"
		return 0
	fi
	[[ -n "$output" ]] && compact_output "$output" >&2
	log_warn "$label failed with exit $code"
	return 2
}

add_existing_file() {
	local candidate="$1"
	[[ -f "$candidate" ]] && printf '%s\n' "$candidate"
}

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

sys.exit(1)
PY
}

pytest_runner_command() {
	local arg uv_args=()
	if command_exists uv && [[ -f pyproject.toml ]]; then
		while IFS= read -r arg; do
			[[ -n "$arg" ]] && uv_args+=("$arg")
		done < <(uv_pytest_prefix_args)
		if [[ "${#uv_args[@]}" -gt 0 ]] && uv "${uv_args[@]}" python -c 'import pytest' >/dev/null 2>&1; then
			printf '%s\n' uv "${uv_args[@]}" pytest
			return 0
		fi
	fi
	if [[ -x .venv/bin/pytest ]]; then
		printf '%s\n' .venv/bin/pytest
		return 0
	fi
	if command_exists python3 && python3 -c "import pytest" 2>/dev/null; then
		printf '%s\n' python3 -m pytest
		return 0
	fi
	return 1
}

find_python_tests_for_source() {
	local file="$1" dir base
	dir=$(dirname "$file")
	base=$(basename "$file" .py)
	add_existing_file "$dir/test_${base}.py"
	add_existing_file "$dir/${base}_test.py"
	for test_dir in tests test; do
		[[ -d "$test_dir" ]] || continue
		find "$test_dir" -type f \( -name "test_${base}.py" -o -name "${base}_test.py" \) 2>/dev/null
	done
}

run_python_tests() {
	local focus_files=("$@")
	local tests=()
	local file base tmp runner=()
	for file in "${focus_files[@]}"; do
		[[ "$file" == *.py ]] || continue
		base=$(basename "$file")
		# Only genuine pytest test modules (test_*.py / *_test.py) are valid
		# targets. Support files under a test dir — conftest.py, __init__.py,
		# fixtures/helpers — are NOT test modules; passing them to pytest
		# collects nothing (exit 5). Route everything else through source
		# mapping, which finds the related test module if one exists.
		if [[ "$base" == test_*.py || "$base" == *_test.py ]]; then
			tests+=("$file")
		else
			while IFS= read -r candidate; do
				[[ -n "$candidate" ]] && tests+=("$candidate")
			done < <(find_python_tests_for_source "$file")
		fi
	done
	[[ "${#tests[@]}" -gt 0 ]] || return 0
	tmp=$(mktemp 2>/dev/null || printf '/tmp/cc-thingz-python-tests.%s' "$$")
	printf '%s\n' "${tests[@]}" | unique_lines >"$tmp"
	tests=()
	while IFS= read -r file; do tests+=("$file"); done <"$tmp"
	rm -f "$tmp"
	while IFS= read -r file; do
		[[ -n "$file" ]] && runner+=("$file")
	done < <(pytest_runner_command)
	if [[ "${#runner[@]}" -eq 0 ]]; then
		log_warn "pytest not found — skipping focused Python tests"
		return 0
	fi
	runner+=(-q --maxfail=1 --tb=short)
	run_pytest_compact "Python tests" "${runner[@]}" "${tests[@]}"
}

run_go_tests() {
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
		log_warn "go not found — skipping focused Go tests"
		return 0
	}
	tmp=$(mktemp 2>/dev/null || printf '/tmp/cc-thingz-go-tests.%s' "$$")
	printf '%s\n' "${dirs[@]}" | unique_lines >"$tmp"
	local status=0
	while IFS= read -r pkg; do
		[[ -n "$pkg" ]] || continue
		run_and_capture "Go tests" go test -failfast "$pkg" || status=2
	done <"$tmp"
	rm -f "$tmp"
	return "$status"
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
	local file="$1" dir stem
	dir=$(dirname "$file")
	stem=$(basename "$file")
	stem=${stem%.*}
	find "$dir" -maxdepth 1 -type f \( -name "${stem}.test.*" -o -name "${stem}.spec.*" -o -name "test_${stem}.*" \) 2>/dev/null
	for test_dir in tests test src; do
		[[ -d "$test_dir" ]] || continue
		find "$test_dir" -type f \( -name "${stem}.test.*" -o -name "${stem}.spec.*" -o -name "test_${stem}.*" \) 2>/dev/null
	done
}

js_runner_command() {
	local bin has_test_config=0
	if find . -maxdepth 3 -name 'vitest.config.*' -print -quit 2>/dev/null | grep -q .; then
		has_test_config=1
		bin=$(resolve_node_tool vitest || true)
		if [[ -n "$bin" ]]; then
			printf 'vitest|%s\n' "$bin"
			return 0
		fi
	fi
	if find . -maxdepth 3 -name 'jest.config.*' -print -quit 2>/dev/null | grep -q .; then
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
	return 1
}

run_javascript_tests() {
	local focus_files=("$@")
	local tests=()
	local mapped_tests=()
	local sources=()
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
			while IFS= read -r candidate; do
				[[ -n "$candidate" ]] && mapped_tests+=("$candidate")
			done < <(find_js_tests_for_source "$file")
		fi
	done
	[[ "${#sources[@]}" -gt 0 || "${#tests[@]}" -gt 0 || "${#mapped_tests[@]}" -gt 0 ]] || return 0

	runner=$(js_runner_command || true)
	if [[ -z "$runner" ]]; then
		log_warn "No focused JS test runner found — skipping JS tests"
		return 0
	fi

	tmp=$(mktemp 2>/dev/null || printf '/tmp/cc-thingz-js-tests.%s' "$$")
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
			run_and_capture "JS related tests (vitest)" "$bin" related "${sources[@]}" --run --passWithNoTests || status=2
		fi
		if [[ "${#tests[@]}" -gt 0 ]]; then
			run_and_capture "JS tests (vitest)" "$bin" run "${tests[@]}" --passWithNoTests || status=2
		fi
		;;
	jest)
		if [[ "${#sources[@]}" -gt 0 ]]; then
			run_and_capture "JS related tests (jest)" "$bin" --findRelatedTests "${sources[@]}" --passWithNoTests || status=2
		fi
		if [[ "${#tests[@]}" -gt 0 ]]; then
			run_and_capture "JS tests (jest)" "$bin" "${tests[@]}" --passWithNoTests || status=2
		fi
		;;
	bun)
		tests+=("${mapped_tests[@]}")
		[[ "${#tests[@]}" -gt 0 ]] || return 0
		run_and_capture "JS tests (bun)" bun test "${tests[@]}" || status=2
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
	vitest) run_and_capture "vitest" "$bin" run --passWithNoTests ;;
	jest) run_and_capture "jest" "$bin" --passWithNoTests ;;
	bun) run_and_capture "bun test" bun test ;;
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
		log_warn "bats not found — skipping focused shell tests"
		return 0
	}
	tmp=$(mktemp 2>/dev/null || printf '/tmp/cc-thingz-shell-tests.%s' "$$")
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
		log_warn "bats not found — skipping full shell tests"
		return 0
	}
	tmp=$(mktemp 2>/dev/null || printf '/tmp/cc-thingz-full-shell-tests.%s' "$$")
	printf '%s\n' "${tests[@]}" | unique_lines >"$tmp"
	tests=()
	while IFS= read -r file; do tests+=("$file"); done <"$tmp"
	rm -f "$tmp"
	run_and_capture "Shell tests" bats "${tests[@]}"
}

run_full_override() {
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
		run_and_capture "go test" go test -failfast ./...
		return $?
	fi
	local pytest_runner=() pytest_arg
	while IFS= read -r pytest_arg; do
		[[ -n "$pytest_arg" ]] && pytest_runner+=("$pytest_arg")
	done < <(pytest_runner_command)
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
	log_warn "No full project test runner found"
	return 0
}

main() {
	init_hook_input
	maybe_cd_to_hook_cwd

	if [[ "${SKIP_TESTS:-}" == "1" ]] || [[ -f ".notests" ]]; then
		echo -e "${CYAN}⏭ Tests skipped${NC}" >&2
		clear_hook_state
		exit 0
	fi

	echo "" >&2
	echo "🧪 Running focused tests..." >&2
	echo "─────────────────────────" >&2

	if [[ "$TEST_RUNNER_FULL" == "1" ]]; then
		run_full_override
		status=$?
		[[ "$status" -eq 0 ]] && clear_hook_state
		exit "$status"
	fi

	local focus_files=()
	local file
	while IFS= read -r file; do
		[[ -n "$file" ]] && focus_files+=("$file")
	done < <(collect_focus_files)

	if [[ "${#focus_files[@]}" -eq 0 ]]; then
		log_info "No changed code files with focused test support"
		clear_hook_state
		exit 0
	fi

	log_debug "Focus files: ${focus_files[*]}"
	local status=0
	run_python_tests "${focus_files[@]}" || status=2
	run_go_tests "${focus_files[@]}" || status=2
	run_javascript_tests "${focus_files[@]}" || status=2
	run_shell_tests "${focus_files[@]}" || status=2
	if [[ "$status" -eq 0 && "$TESTS_RAN" -eq 0 ]]; then
		run_package_test_fallback || status=2
	fi

	echo "" >&2
	if [[ "$status" -eq 0 ]]; then
		echo -e "${GREEN}✅ Focused tests passed or no targeted tests found${NC}" >&2
		clear_hook_state
	else
		echo -e "${RED}❌ Focused tests failed${NC}" >&2
	fi
	exit "$status"
}

main "$@"
