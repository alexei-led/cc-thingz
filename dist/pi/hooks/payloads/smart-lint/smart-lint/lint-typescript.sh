#!/usr/bin/env bash
# JavaScript/TypeScript linting: Oxfmt/Biome/Oxlint when available, then legacy tools.

lint_typescript() {
	log_debug "js/ts checks"

	local files=()
	while IFS= read -r file; do
		files+=("$file")
	done < <(get_changed_files ".js" ".mjs" ".cjs" ".jsx" ".ts" ".mts" ".cts" ".tsx")
	if [[ "${#files[@]}" -eq 0 ]]; then
		log_debug "No uncommitted JS/TS files, skipping JavaScript checks"
		return 0
	fi

	local biome_bin="" oxfmt_bin="" oxlint_bin="" prettier_bin="" eslint_bin=""
	local formatter_kind="none" linter_kind="none"
	local biome_project=0 oxfmt_project=0 oxlint_project=0 prettier_project=0 eslint_project=0
	node_tool_is_adopted biome && biome_project=1
	node_tool_is_adopted oxfmt && oxfmt_project=1
	node_tool_is_adopted oxlint && oxlint_project=1
	node_tool_is_adopted prettier && prettier_project=1
	node_tool_is_adopted eslint && eslint_project=1

	# A project declaration wins for that capability. If the declared binary is
	# missing, the same capability falls back through the available tools.
	if [[ "$oxfmt_project" -eq 1 ]]; then
		oxfmt_bin=$(resolve_node_tool oxfmt || true)
		[[ -n "$oxfmt_bin" ]] && formatter_kind="oxfmt"
	fi
	if [[ "$formatter_kind" == "none" && "$biome_project" -eq 1 ]]; then
		biome_bin=$(resolve_node_tool biome || true)
		[[ -n "$biome_bin" ]] && formatter_kind="biome"
	fi
	if [[ "$formatter_kind" == "none" && "$prettier_project" -eq 1 ]]; then
		prettier_bin=$(resolve_node_tool prettier || true)
		[[ -n "$prettier_bin" ]] && formatter_kind="prettier"
	fi
	if [[ "$formatter_kind" == "none" ]]; then
		oxfmt_bin=$(resolve_node_tool oxfmt || true)
		if [[ -n "$oxfmt_bin" ]]; then
			formatter_kind="oxfmt"
		else
			biome_bin=$(resolve_node_tool biome || true)
			if [[ -n "$biome_bin" ]]; then
				formatter_kind="biome"
			else
				prettier_bin=$(resolve_node_tool prettier || true)
				[[ -n "$prettier_bin" ]] && formatter_kind="prettier"
			fi
		fi
	fi

	if [[ "$oxlint_project" -eq 1 ]]; then
		oxlint_bin=$(resolve_node_tool oxlint || true)
		[[ -n "$oxlint_bin" ]] && linter_kind="oxlint"
	fi
	if [[ "$linter_kind" == "none" && "$biome_project" -eq 1 ]]; then
		[[ -n "$biome_bin" ]] || biome_bin=$(resolve_node_tool biome || true)
		[[ -n "$biome_bin" ]] && linter_kind="biome"
	fi
	if [[ "$linter_kind" == "none" && "$eslint_project" -eq 1 ]]; then
		eslint_bin=$(resolve_node_tool eslint || true)
		[[ -n "$eslint_bin" ]] && linter_kind="eslint"
	fi
	if [[ "$linter_kind" == "none" ]]; then
		# No project linter declaration: prefer the fastest installed linter.
		oxlint_bin=$(resolve_node_tool oxlint || true)
		if [[ -n "$oxlint_bin" ]]; then
			linter_kind="oxlint"
		else
			biome_bin=$(resolve_node_tool biome || true)
			if [[ -n "$biome_bin" ]]; then
				linter_kind="biome"
			else
				eslint_bin=$(resolve_node_tool eslint || true)
				[[ -n "$eslint_bin" ]] && linter_kind="eslint"
			fi
		fi
	fi

	if [[ "$formatter_kind" == "biome" && "$linter_kind" == "biome" ]]; then
		# Biome's combined check avoids formatting and linting the same file twice.
		mark_format_ran
		mark_lint_ran
		run_command_compact "JS/TS Checks (biome)" "$biome_bin" check --write "${files[@]}"
	else
		case "$formatter_kind" in
		oxfmt) run_formatter_on_files --format-only "JS Formatter (oxfmt)" "$oxfmt_bin --write" "" "${files[@]}" ;;
		biome) run_formatter_on_files --format-only "JS Formatter (biome)" "$biome_bin format --write" "" "${files[@]}" ;;
		prettier) run_formatter_on_files --format-only "JS Formatter (prettier)" "$prettier_bin --write" "" "${files[@]}" ;;
		esac
		case "$linter_kind" in
		oxlint) run_linter_compact "JS Linter (oxlint)" "$oxlint_bin" --fix "${files[@]}" ;;
		biome) run_linter_compact "JS Linter (biome)" "$biome_bin" lint --write "${files[@]}" ;;
		eslint)
			# Keep post-edit JS lint file-scoped. Project-wide package scripts belong
			# in the explicit project fallback or pre-commit/CI.
			run_linter_compact "JS Linter (eslint)" "$eslint_bin" --fix "${files[@]}"
			;;
		esac
	fi
}
