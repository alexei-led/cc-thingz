#!/usr/bin/env bash
# Go linting: gofmt, golangci-lint (or go vet fallback), make lint if present.

lint_go() {
	log_debug "go checks"

	local files=()
	while IFS= read -r file; do
		files+=("$file")
	done < <(get_changed_files ".go")
	if [[ "${#files[@]}" -eq 0 ]]; then
		log_debug "No uncommitted Go files, skipping Go checks"
		return 0
	fi

	if command_exists gofmt; then
		run_formatter_on_files --format-only "Go Formatter (gofmt)" "gofmt -w" "" "${files[@]}"
	fi
	# golangci-lint and go vet both expect package dirs, not individual files.
	# Keep post-edit lint package-scoped; project-wide `make lint` belongs in
	# pre-commit/CI, not the interactive hook path.
	local pkg_dirs=()
	local dir
	for file in "${files[@]}"; do
		dir=$(dirname "$file")
		[[ "$dir" == "." ]] && pkg_dirs+=(".") || pkg_dirs+=("./$dir")
	done
	local unique_packages=()
	local pkg_dir
	while IFS= read -r pkg_dir; do
		[[ -n "$pkg_dir" ]] && unique_packages+=("$pkg_dir")
	done < <(printf '%s\n' "${pkg_dirs[@]}" | sort -u)

	if command_exists golangci-lint; then
		local version
		version=$(golangci-lint version --short 2>/dev/null)
		local base_cmd=(golangci-lint run --fix)
		if [[ "$version" == 2* ]]; then
			base_cmd+=(--fast-only)
		else
			base_cmd+=(--fast)
		fi

		if output=$("${base_cmd[@]}" "${unique_packages[@]}" 2>&1); then
			log_debug "golangci-lint passed"
		else
			# Retry with --no-config if config error
			if echo "$output" | grep -q "Error: can't load config"; then
				log_info "Config error detected, retrying with --no-config..."
				if output=$("${base_cmd[@]}" --no-config "${unique_packages[@]}" 2>&1); then
					return 0
				fi
			fi
			add_error "Go (golangci-lint)" "$(compact_output "$output")"
		fi
	elif command_exists go; then
		if [[ ${#unique_packages[@]} -gt 0 ]]; then
			run_linter_compact "Go (go vet)" go vet "${unique_packages[@]}"
		fi
	fi
}
