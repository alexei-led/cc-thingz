#!/usr/bin/env bash
# Shell script linting: shellcheck, shfmt. Skips .claude-hooks-config.sh (sourced, not executed).

lint_shell() {
	log_debug "shell checks"

	local files=()
	while IFS= read -r file; do
		files+=("$file")
	done < <(get_changed_files ".sh" ".bash")
	if [[ "${#files[@]}" -eq 0 ]]; then
		log_debug "No uncommitted shell files, skipping shell checks"
		return 0
	fi

	# Filter out hook config files — they are sourced, not executed, and
	# users routinely write them without shebangs (one-liners like
	# `export SKIP_ARCH=1`). Linting them would block edits.
	local filtered=()
	for file in "${files[@]}"; do
		if [[ "$(basename "$file")" == ".claude-hooks-config.sh" ]]; then
			log_debug "Skipping hook config file: $file"
			continue
		fi
		filtered+=("$file")
	done
	if [[ "${#filtered[@]}" -eq 0 ]]; then
		return 0
	fi

	if command_exists shellcheck; then
		run_linter_compact "Shell Linter (shellcheck)" shellcheck "${filtered[@]}"
	fi
	if command_exists shfmt; then
		run_formatter_on_files --format-only "Shell Formatter (shfmt)" "shfmt -w" "" "${filtered[@]}"
	fi
}
