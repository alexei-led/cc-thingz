#!/usr/bin/env bash
# C# /.NET linting: focused dotnet format on changed files or nearest safe targets.

csharp_find_containing_solution() {
	local file="$1" dir candidate
	dir=$(dirname "$file")
	while [[ -n "$dir" && "$dir" != "/" ]]; do
		candidate=$(find "$dir" -maxdepth 1 -type f -name "*.sln" | sort | head -n 1)
		[[ -n "$candidate" ]] && {
			printf '%s\n' "$candidate"
			return 0
		}
		[[ "$dir" == "." ]] && break
		dir=$(dirname "$dir")
	done
	candidate=$(find . -maxdepth 1 -type f -name "*.sln" | sort | head -n 1)
	[[ -n "$candidate" ]] && printf '%s\n' "$candidate"
}

csharp_find_nearest_csproj() {
	local file="$1" dir candidate
	if [[ "$file" == *.csproj && -f "$file" ]]; then
		printf '%s\n' "$file"
		return 0
	fi
	dir=$(dirname "$file")
	while [[ -n "$dir" && "$dir" != "/" ]]; do
		candidate=$(find "$dir" -maxdepth 1 -type f -name "*.csproj" | sort | head -n 1)
		[[ -n "$candidate" ]] && {
			printf '%s\n' "$candidate"
			return 0
		}
		[[ "$dir" == "." ]] && break
		dir=$(dirname "$dir")
	done
	candidate=$(find . -maxdepth 1 -type f -name "*.csproj" | sort | head -n 1)
	[[ -n "$candidate" ]] && printf '%s\n' "$candidate"
}

csharp_relative_to_target_dir() {
	local target="$1" file="$2" target_dir prefix
	target_dir=$(dirname "$target")
	if [[ "$target_dir" == "." ]]; then
		printf '%s\n' "$file"
		return 0
	fi
	prefix="${target_dir%/}/"
	printf '%s\n' "${file#"$prefix"}"
}

csharp_run_dotnet_format() {
	local target="$1"
	shift
	local target_dir target_name output

	mark_format_ran
	mark_lint_ran
	target_dir=$(dirname "$target")
	target_name=$(basename "$target")
	if output=$(cd "$target_dir" && dotnet format "$target_name" "$@" 2>&1); then
		log_debug "dotnet format passed for $target $*"
		return 0
	fi
	add_error "C# Formatter/Linter (dotnet format)" "$(compact_output "$output")"
	return 2
}

lint_csharp() {
	log_debug "csharp checks"

	local files=()
	while IFS= read -r file; do
		files+=("$file")
	done < <(get_changed_files ".cs" ".csproj" ".sln" ".props" ".targets")
	if [[ "${#files[@]}" -eq 0 ]]; then
		log_debug "No uncommitted C#/.NET files, skipping C# checks"
		return 0
	fi

	command_exists dotnet || {
		log_info "dotnet not found — skipping focused C# lint"
		return 0
	}

	local file target include_path status=0
	for file in "${files[@]}"; do
		case "$file" in
		*.cs)
			target=$(csharp_find_nearest_csproj "$file" || true)
			[[ -z "$target" ]] && target=$(csharp_find_containing_solution "$file" || true)
			[[ -n "$target" ]] || continue
			include_path=$(csharp_relative_to_target_dir "$target" "$file")
			csharp_run_dotnet_format "$target" --include "$include_path" || status=2
			;;
		*.csproj | *.sln)
			csharp_run_dotnet_format "$file" || status=2
			;;
		*.props | *.targets)
			target=$(csharp_find_containing_solution "$file" || true)
			[[ -z "$target" ]] && target=$(csharp_find_nearest_csproj "$file" || true)
			[[ -n "$target" ]] || continue
			csharp_run_dotnet_format "$target" || status=2
			;;
		esac
	done
	return "$status"
}
