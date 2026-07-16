#!/usr/bin/env bash
# JavaScript/TypeScript linting: prettier, eslint, knip, dependency-cruiser (arch tier).

lint_typescript() {
	log_debug "js/ts checks"

	local files=()
	while IFS= read -r file; do
		files+=("$file")
	done < <(get_changed_files ".js" ".ts" ".jsx" ".tsx")
	if [[ "${#files[@]}" -eq 0 ]]; then
		log_debug "No uncommitted JS/TS files, skipping JavaScript checks"
		return 0
	fi

	local prettier_bin
	prettier_bin=$(resolve_node_tool prettier || true)
	if [[ -n "$prettier_bin" ]]; then
		run_formatter_on_files --format-only "JS Formatter (prettier)" "$prettier_bin --write" "" "${files[@]}"
	fi

	# Keep post-edit JS lint file-scoped. `npm run lint` and architecture tools
	# commonly scan the whole project, so they belong in pre-commit/CI.
	local eslint_bin
	eslint_bin=$(resolve_node_tool eslint || true)
	if [[ -n "$eslint_bin" ]]; then
		run_linter_compact "JS Linter (eslint)" "$eslint_bin" --fix "${files[@]}"
	fi
}
