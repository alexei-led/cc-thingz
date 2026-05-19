#!/usr/bin/env bash
# Python linting: ruff (format + lint), black + flake8 fallback, pyright type checks.

pyright_compact_json() {
	command_exists python3 || return 2
	python3 -c '
import json
import sys

raw = sys.stdin.read()
try:
    data = json.loads(raw or "{}")
except json.JSONDecodeError:
    sys.exit(2)

diagnostics = data.get("generalDiagnostics", [])
if not isinstance(diagnostics, list):
    sys.exit(2)

lines = []
for item in diagnostics:
    if not isinstance(item, dict):
        continue
    if item.get("rule") == "reportMissingImports":
        continue
    if item.get("severity") != "error":
        continue
    file_name = item.get("file") or "<unknown>"
    range_data = item.get("range") if isinstance(item.get("range"), dict) else {}
    start = range_data.get("start") if isinstance(range_data.get("start"), dict) else {}
    raw_line = start.get("line", 0)
    raw_char = start.get("character", 0)
    line = raw_line + 1 if isinstance(raw_line, int) else 1
    char = raw_char + 1 if isinstance(raw_char, int) else 1
    message = str(item.get("message") or "").replace("\n", " ")
    rule = item.get("rule")
    suffix = f" [{rule}]" if isinstance(rule, str) and rule else ""
    lines.append(f"{file_name}:{line}:{char}: error{suffix}: {message}")

if not lines:
    sys.exit(1)

for line in lines:
    print(line)
'
}

lint_python() {
	log_debug "python checks"

	local files=()
	while IFS= read -r file; do
		files+=("$file")
	done < <(get_changed_files ".py")
	if [[ "${#files[@]}" -eq 0 ]]; then
		log_debug "No uncommitted Python files, skipping Python checks"
		return 0
	fi

	local ruff_runner=()
	if command_exists ruff; then
		ruff_runner=(ruff)
	elif command_exists uv && [[ -f pyproject.toml ]] && python_project_mentions_tool ruff; then
		ruff_runner=(uv run ruff)
	fi

	if [[ "${#ruff_runner[@]}" -gt 0 ]]; then
		# ruff format replaces black — single tool for formatting
		run_formatter_on_files --format-only "Python Formatter (ruff)" "${ruff_runner[*]} format" "" "${files[@]}"
		# --unfixable=F401: report unused imports but don't auto-remove them
		# AI agents add imports in one edit and use them in the next
		run_linter_compact "Python Linter (ruff)" "${ruff_runner[@]}" check --fix --unfixable=F401 "${files[@]}"
	else
		local black_runner=()
		if command_exists black; then
			black_runner=(black)
		elif command_exists uv && [[ -f pyproject.toml ]] && python_project_mentions_tool black; then
			black_runner=(uv run black)
		fi
		if [[ "${#black_runner[@]}" -gt 0 ]]; then
			run_formatter_on_files --format-only "Python Formatter (black)" "${black_runner[*]}" "" "${files[@]}"
		fi
		if command_exists flake8; then
			run_linter_compact "Python Linter (flake8)" flake8 "${files[@]}"
		elif command_exists uv && [[ -f pyproject.toml ]] && python_project_mentions_tool flake8; then
			run_linter_compact "Python Linter (flake8)" uv run flake8 "${files[@]}"
		fi
	fi

	local pyright_runner=()
	local pyright_bin
	pyright_bin=$(resolve_node_tool pyright || true)
	if [[ -n "$pyright_bin" ]]; then
		pyright_runner=("$pyright_bin")
	elif command_exists uv && [[ -f pyproject.toml ]] && python_project_mentions_tool pyright; then
		pyright_runner=(uv run pyright)
	fi
	if [[ "${#pyright_runner[@]}" -gt 0 ]]; then
		# Filter out reportMissingImports — missing stubs, not real errors
		local pyright_output
		if pyright_output=$("${pyright_runner[@]}" --outputjson "${files[@]}" 2>&1); then
			log_debug "pyright passed"
		else
			local filtered parse_status
			filtered=$(pyright_compact_json <<<"$pyright_output")
			parse_status=$?
			if [[ "$parse_status" -eq 0 && -n "$filtered" ]]; then
				add_error "Python Type Checker (pyright)" "$(compact_output "$filtered")"
			elif [[ "$parse_status" -eq 1 ]]; then
				log_debug "pyright: only missing stubs warnings (filtered)"
			else
				filtered=$(printf '%s\n' "$pyright_output" | grep -v 'reportMissingImports')
				if printf '%s\n' "$filtered" | grep -qE ' error: '; then
					add_error "Python Type Checker (pyright)" "$(compact_output "$filtered")"
				else
					log_debug "pyright: only missing stubs warnings (filtered)"
				fi
			fi
		fi
	fi
}
