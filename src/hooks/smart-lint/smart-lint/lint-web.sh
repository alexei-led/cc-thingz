#!/usr/bin/env bash
# Web/config format linting: YAML, JSON, GitHub Actions, Terraform, Markdown.

lint_yaml() {
	log_debug "yaml checks"

	local files=()
	while IFS= read -r file; do
		files+=("$file")
	done < <(get_changed_files ".yaml" ".yml")
	if [[ "${#files[@]}" -eq 0 ]]; then
		log_debug "No uncommitted YAML files, skipping YAML checks"
		return 0
	fi

	if command_exists yq; then
		mark_tool_ran
		# Process each file individually to prevent content merging
		for file in "${files[@]}"; do
			if ! yq eval -P -i "$file" 2>/dev/null; then
				add_error "YAML Formatter (yq)" "Failed to format $file"
			fi
		done
	fi
	if command_exists yamllint; then
		run_linter_compact "YAML Linter (yamllint)" yamllint -d '{extends: default, rules: {line-length: disable, document-start: disable, indentation: disable, truthy: disable, comments: disable}}' "${files[@]}"
	fi
}

lint_json() {
	log_debug "json checks"

	local files=()
	while IFS= read -r file; do
		files+=("$file")
	done < <(get_changed_files ".json")
	if [[ "${#files[@]}" -eq 0 ]]; then
		log_debug "No uncommitted JSON files, skipping JSON checks"
		return 0
	fi

	if command_exists jq; then
		mark_tool_ran
		log_debug "Running JSON formatter on files: ${files[*]}"
		for file in "${files[@]}"; do
			if ! jq . "$file" >"${file}.tmp" 2>/dev/null; then
				rm -f "${file}.tmp"
				add_error "JSON Formatter (jq)" "Failed to format $file"
			elif ! mv "${file}.tmp" "$file"; then
				rm -f "${file}.tmp"
				add_error "JSON Formatter (jq)" "Failed to write $file"
			fi
		done
	else
		local prettier_bin
		prettier_bin=$(resolve_node_tool prettier || true)
		if [[ -n "$prettier_bin" ]]; then
			run_formatter_on_files --format-only "JSON Formatter (prettier)" "$prettier_bin --write" "" "${files[@]}"
		fi
	fi
}

lint_github_actions() {
	log_debug "github actions checks"

	# Check for changed workflow files
	if ! [[ -d ".github/workflows" ]]; then
		return 0
	fi

	local files=()
	while IFS= read -r file; do
		files+=("$file")
	done < <(get_changed_files ".yaml" ".yml" | grep -F ".github/workflows/" || true)
	if [[ "${#files[@]}" -eq 0 ]]; then
		log_debug "No uncommitted GitHub Actions workflow files, skipping actionlint"
		return 0
	fi

	if command_exists actionlint; then
		run_linter_compact "GitHub Actions Linter (actionlint)" actionlint "${files[@]}"
	fi
}

lint_terraform() {
	log_debug "terraform checks"

	local files=()
	while IFS= read -r file; do
		files+=("$file")
	done < <(get_changed_files ".tf" ".tfvars")
	if [[ "${#files[@]}" -eq 0 ]]; then
		log_debug "No uncommitted Terraform files, skipping Terraform checks"
		return 0
	fi

	if command_exists terraform; then
		mark_tool_ran
		log_debug "Found changed Terraform files, running terraform fmt on edited files"
		if ! output=$(terraform fmt "${files[@]}" 2>&1); then
			add_error "Terraform Formatter" "$(compact_output "$output")"
		fi
	fi
}

lint_markdown() {
	log_debug "markdown checks"

	local files=()
	while IFS= read -r file; do
		files+=("$file")
	done < <(get_changed_files ".md")
	if [[ "${#files[@]}" -eq 0 ]]; then
		log_debug "No uncommitted Markdown files, skipping Markdown checks"
		return 0
	fi

	# Filter out slides.md and symlinks (prettier errors on symlinks)
	local filtered_files=()
	for file in "${files[@]}"; do
		if [[ -L "$file" ]]; then
			log_debug "Skipping symlink: $file"
		elif [[ "$(basename "$file")" == "slides.md" ]]; then
			log_debug "Skipping Slidev file: $file"
		else
			filtered_files+=("$file")
		fi
	done

	if [[ "${#filtered_files[@]}" -eq 0 ]]; then
		log_debug "No Markdown files to lint after filtering"
		return 0
	fi

	local absolute_files=()
	for file in "${filtered_files[@]}"; do
		absolute_files+=("$(pwd)/${file}")
	done

	local prettier_bin
	prettier_bin=$(resolve_node_tool prettier || true)
	if [[ -n "$prettier_bin" ]]; then
		run_formatter_on_files --format-only "Markdown Formatter (prettier)" "$prettier_bin --write" "" "${absolute_files[@]}"
	elif command_exists mdformat; then
		run_formatter_on_files --format-only "Markdown Formatter (mdformat)" "mdformat" "" "${filtered_files[@]}"
	fi
	if command_exists markdownlint; then
		run_linter_compact "Markdown Linter (markdownlint)" markdownlint --disable MD013 MD026 MD033 MD040 MD041 -- "${filtered_files[@]}"
	fi
}
