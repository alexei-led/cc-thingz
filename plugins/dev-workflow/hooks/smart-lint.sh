#!/usr/bin/env bash
# smart-lint.sh - Concise, project-aware code quality checks.
#
# DESCRIPTION
#   Auto-detects project type and runs formatters and linters.
#   All issues are blocking; the script attempts to auto-fix where possible.
#
# OPTIONS
#   --debug       Enable debug output.
#
# EXIT CODES
#   0 - All checks passed successfully
#   1 - Blocking issues found that need to be fixed

set -o pipefail
set +e

# --- UTILITIES ---
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'
CLAUDE_HOOKS_DEBUG="${CLAUDE_HOOKS_DEBUG:-0}"

log_debug() { [[ "$CLAUDE_HOOKS_DEBUG" == "1" ]] && echo -e "${CYAN}[DEBUG]${NC} $*" >&2; }
log_info() { echo -e "${BLUE}[INFO]${NC} $*" >&2; }
command_exists() { command -v "$1" &>/dev/null; }

# --- SKIP CHECK ---
# Skip linting via env var (transient: SKIP_LINT=1 <command>)
# or via .nolint file in project root (persistent; add to .gitignore).
# Skip just the architecture-tier tools (knip, dependency-cruiser, …) via
# .nolint-arch or SKIP_ARCH=1 — fast linters still run.
if [[ "${SKIP_LINT:-}" == "1" ]] || [[ -f ".nolint" ]]; then
	echo -e "${CYAN}⏭ Linting skipped${NC}" >&2
	exit 0
fi
[[ -f ".nolint-arch" ]] && SKIP_ARCH=1

# --- ERROR & SUMMARY ---
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
		# Include token monitoring inline
		local total_words=0
		local w
		# CLAUDE.md + settings
		for f in ~/.claude/CLAUDE.md ~/.claude/.claude/CLAUDE.md ~/.claude/settings.json; do
			[[ -f "$f" ]] && {
				w=$(wc -w <"$f" 2>/dev/null | tr -d ' ')
				total_words=$((total_words + w))
			}
		done
		# Commands, skills, agents (top-level .md only)
		for f in ~/.claude/commands/*.md ~/.claude/commands/**/*.md \
			~/.claude/skills/*/SKILL.md ~/.claude/agents/*.md ~/.claude/agents/**/*.md; do
			[[ -f "$f" ]] && {
				w=$(wc -w <"$f" 2>/dev/null | tr -d ' ')
				total_words=$((total_words + w))
			}
		done
		local approx_tokens=$((total_words * 4 / 3))
		echo -e "${PROJECT_TYPE} project ${GREEN}✅ Style OK${NC} ${CYAN}📊 ~${approx_tokens} tokens${NC}" >&2
		exit 0 # Exit successfully when all checks pass
	fi
}

# --- CHANGED FILES DETECTION ---
get_changed_files() {
	# Usage: get_changed_files ".go" or get_changed_files ".js" ".ts" ".jsx" ".tsx"
	local extensions=("$@")

	if ! git rev-parse --git-dir >/dev/null 2>&1; then
		return
	fi

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

	# ACMRTUXB = Added, Copied, Modified, Renamed, Type-changed, Unmerged, Unknown, Broken
	# Exclude D (Deleted) as those files don't exist to lint
	{
		git diff --name-only --diff-filter=ACMRTUXB --cached HEAD 2>/dev/null || true
		git diff --name-only --diff-filter=ACMRTUXB 2>/dev/null || true
		git ls-files --others --exclude-standard 2>/dev/null || true
	} | sort -u | while IFS= read -r file; do
		if [[ -n "$file" && -f "$file" ]]; then
			local skip=0
			for pattern in "${exclude_patterns[@]}"; do
				if [[ "$file" == *"$pattern"* ]]; then
					skip=1
					break
				fi
			done
			if [[ $skip -eq 0 ]]; then
				for ext in "${extensions[@]}"; do
					if [[ "$file" == *"$ext" ]]; then
						echo "$file"
						break
					fi
				done
			fi
		fi
	done
}

# --- FORMATTER HELPERS ---
run_formatter_on_files() {
	local name="$1" format_cmd="$2" check_cmd="$3"
	shift 3
	local files=("$@")

	if [[ "${#files[@]}" -eq 0 ]]; then
		log_debug "No files to format, skipping $name"
		return 0
	fi

	log_debug "Running $name on files: ${files[*]}"

	# Format files
	$format_cmd "${files[@]}" >/dev/null 2>&1

	# Check if issues remain
	if output=$($check_cmd "${files[@]}" 2>&1); then
		return 0 # All good
	else
		add_error "$name needs fixing" "$output"
	fi
}

run_linter() {
	local name="$1"
	shift
	if output=$("$@" 2>&1); then
		log_debug "$name passed."
		return 0
	else
		add_error "$name found issues" "$output"
	fi
}

# --- PROJECT DETECTION ---
detect_project_type() {
	local project_type="unknown"
	local types=()

	# Go project
	if [[ -f "go.mod" ]] || [[ -f "go.sum" ]] || [[ -n "$(find . -maxdepth 3 -name "*.go" -type f -print -quit 2>/dev/null)" ]]; then
		types+=("go")
	fi
	# Python project
	if [[ -f "pyproject.toml" ]] || [[ -f "setup.py" ]] || [[ -f "requirements.txt" ]] || [[ -n "$(find . -maxdepth 3 -name "*.py" -type f -print -quit 2>/dev/null)" ]]; then
		types+=("python")
	fi
	# JavaScript/TypeScript project
	if [[ -f "package.json" ]] || [[ -f "tsconfig.json" ]] || [[ -n "$(find . -maxdepth 3 \( -name "*.js" -o -name "*.ts" -o -name "*.jsx" -o -name "*.tsx" \) -type f -print -quit 2>/dev/null)" ]]; then
		types+=("javascript")
	fi
	# YAML files
	if [[ -n "$(find . -maxdepth 3 \( -name "*.yaml" -o -name "*.yml" \) -type f -print -quit 2>/dev/null)" ]]; then
		types+=("yaml")
	fi
	# JSON files
	if [[ -n "$(find . -maxdepth 3 -name "*.json" -type f -print -quit 2>/dev/null)" ]]; then
		types+=("json")
	fi
	# Shell scripts
	if [[ -n "$(find . -maxdepth 3 \( -name "*.sh" -o -name "*.bash" \) -type f -print -quit 2>/dev/null)" ]]; then
		types+=("shell")
	fi
	# GitHub Actions
	if [[ -d ".github/workflows" ]]; then
		types+=("github_actions")
	fi
	# Terraform
	if [[ -n "$(find . -maxdepth 3 \( -name "*.tf" -o -name "*.tfvars" \) -type f -print -quit 2>/dev/null)" ]]; then
		types+=("terraform")
	fi
	# Markdown files
	if [[ -n "$(find . -maxdepth 3 -name "*.md" -type f -print -quit 2>/dev/null)" ]]; then
		types+=("markdown")
	fi

	# Return primary type or "mixed" if multiple
	if [[ ${#types[@]} -eq 1 ]]; then
		project_type="${types[0]}"
	elif [[ ${#types[@]} -gt 1 ]]; then
		project_type="mixed:$(
			IFS=,
			echo "${types[*]}"
		)"
	fi
	log_debug "Detected project type: $project_type"
	echo "$project_type"
}

# --- LANGUAGE LINTERS ---

lint_go() {
	log_debug "go checks"

	# Get changed Go files early
	local files=()
	mapfile -t files < <(get_changed_files ".go")
	if [[ "${#files[@]}" -eq 0 ]]; then
		log_debug "No uncommitted Go files, skipping Go checks"
		return 0
	fi

	if [[ -f "Makefile" ]] && grep -q -E "^lint:" Makefile; then
		run_linter "Go (make lint)" make lint
	else
		if command_exists gofmt; then
			run_formatter_on_files "Go Formatter (gofmt)" "gofmt -w" "gofmt -l" "${files[@]}"
		fi
		if command_exists golangci-lint; then
			# Pass specific files to golangci-lint instead of scanning everything
			local version
			version=$(golangci-lint version --short 2>/dev/null)
			local base_cmd=(golangci-lint run --fix)
			if [[ "$version" == 2* ]]; then
				base_cmd+=(--fast-only)
			else
				base_cmd+=(--fast)
			fi

			if output=$("${base_cmd[@]}" "${files[@]}" 2>&1); then
				log_debug "golangci-lint passed"
			else
				# Retry with --no-config if config error
				if echo "$output" | grep -q "Error: can't load config"; then
					log_info "Config error detected, retrying with --no-config..."
					if output=$("${base_cmd[@]}" --no-config "${files[@]}" 2>&1); then
						return 0
					fi
				fi
				add_error "Go (golangci-lint)" "$output"
			fi
		elif command_exists go; then
			# go vet expects package paths, not individual files
			# Extract unique directories (packages) from changed files
			local -A pkg_map
			for file in "${files[@]}"; do
				local pkg_dir
				pkg_dir=$(dirname "$file")
				pkg_map["$pkg_dir"]=1
			done
			# Get unique packages as array
			local unique_packages=("${!pkg_map[@]}")
			if [[ ${#unique_packages[@]} -gt 0 ]]; then
				run_linter "Go (go vet)" go vet "${unique_packages[@]}"
			fi
		fi
	fi
}

lint_python() {
	log_debug "python checks"

	# Get changed Python files early
	local files=()
	mapfile -t files < <(get_changed_files ".py")
	if [[ "${#files[@]}" -eq 0 ]]; then
		log_debug "No uncommitted Python files, skipping Python checks"
		return 0
	fi

	if command_exists ruff; then
		# ruff format replaces black — single tool for formatting
		run_formatter_on_files "Python Formatter (ruff)" "ruff format" "ruff format --check" "${files[@]}"
		# --unfixable=F401: report unused imports but don't auto-remove them
		# AI agents add imports in one edit and use them in the next
		run_linter "Python Linter (ruff)" ruff check --fix --unfixable=F401 "${files[@]}"
	else
		if command_exists black; then
			run_formatter_on_files "Python Formatter (black)" "black" "black --check" "${files[@]}"
		fi
		if command_exists flake8; then
			run_linter "Python Linter (flake8)" flake8 "${files[@]}"
		fi
	fi
	if command_exists pyright; then
		# Filter out reportMissingImports — missing stubs, not real errors
		local pyright_output
		if pyright_output=$(pyright "${files[@]}" 2>&1); then
			log_debug "pyright passed"
		else
			local filtered
			filtered=$(echo "$pyright_output" | grep -v 'reportMissingImports')
			if echo "$filtered" | grep -qE ' error: '; then
				add_error "Python Type Checker (pyright)" "$filtered"
			else
				log_debug "pyright: only missing stubs warnings (filtered)"
			fi
		fi
	fi
}

lint_javascript() {
	log_debug "js/ts checks"

	# Get changed JS/TS files early
	local files=()
	mapfile -t files < <(get_changed_files ".js" ".ts" ".jsx" ".tsx")
	if [[ "${#files[@]}" -eq 0 ]]; then
		log_debug "No uncommitted JS/TS files, skipping JavaScript checks"
		return 0
	fi

	local pm="npm"
	[[ -f "yarn.lock" ]] && pm="yarn"
	[[ -f "pnpm-lock.yaml" ]] && pm="pnpm"

	# Use prettier if available, otherwise try via package manager
	if command_exists prettier; then
		run_formatter_on_files "JS Formatter (prettier)" "prettier --write" "prettier --check" "${files[@]}"
	elif command_exists bunx; then
		run_formatter_on_files "JS Formatter (prettier)" "bunx prettier --write" "bunx prettier --check" "${files[@]}"
	elif command_exists npx; then
		run_formatter_on_files "JS Formatter (prettier)" "npx prettier --write" "npx prettier --check" "${files[@]}"
	elif [[ "$pm" != "npm" ]]; then
		run_formatter_on_files "JS Formatter (prettier)" "$pm exec prettier --write" "$pm exec prettier --check" "${files[@]}"
	fi
	if grep -q '"lint":' package.json 2>/dev/null; then
		# Note: npm run lint typically runs on whole project, might need package.json config for file-specific linting
		run_linter "JS Linter (eslint)" "$pm" run lint --if-present
	fi

	# Architecture tier — opt-in by config-file presence. Skipped via SKIP_ARCH=1
	# or .nolint-arch. Project-wide tools, so they don't take the file list.
	[[ "${SKIP_ARCH:-0}" == "1" ]] && return 0

	# knip — unused exports, files, deps. Triggers on its own config file.
	# --max-issues 0 ensures non-zero exit on any finding (knip's default tolerates one).
	if [[ -f knip.json || -f knip.jsonc || -f knip.ts || -f knip.js ]]; then
		if command_exists knip; then
			run_linter "Knip" knip --reporter compact --no-progress --max-issues 0
		elif command_exists bunx; then
			run_linter "Knip" bunx knip --reporter compact --no-progress --max-issues 0
		elif command_exists npx; then
			run_linter "Knip" npx knip --reporter compact --no-progress --max-issues 0
		else
			echo -e "${CYAN}ℹ knip config present but no runner found. Install:${NC} bun add -g knip"
		fi
	fi

	# dependency-cruiser — boundary rules and import cycles. CLI is `depcruise`.
	# `-T err` reporter exits non-zero on violations (default reporter does not).
	if [[ -f .dependency-cruiser.cjs || -f .dependency-cruiser.js || -f .dependency-cruiser.json || -f .dependency-cruiser.mjs ]]; then
		local dc_target="."
		[[ -d src ]] && dc_target="src"
		if command_exists depcruise; then
			run_linter "Dependency-Cruiser" depcruise -T err "$dc_target"
		elif command_exists bunx; then
			run_linter "Dependency-Cruiser" bunx depcruise -T err "$dc_target"
		elif command_exists npx; then
			run_linter "Dependency-Cruiser" npx depcruise -T err "$dc_target"
		else
			echo -e "${CYAN}ℹ dependency-cruiser config present but no runner found. Install:${NC} bun add -g dependency-cruiser"
		fi
	fi
}

lint_yaml() {
	log_debug "yaml checks"

	# Get changed YAML files early
	local files=()
	mapfile -t files < <(get_changed_files ".yaml" ".yml")
	if [[ "${#files[@]}" -eq 0 ]]; then
		log_debug "No uncommitted YAML files, skipping YAML checks"
		return 0
	fi

	if command_exists yq; then
		# Process each file individually to prevent content merging
		for file in "${files[@]}"; do
			if ! yq eval -P -i "$file" 2>/dev/null; then
				add_error "YAML Formatter (yq)" "Failed to format $file"
			fi
		done
	fi
	if command_exists yamllint; then
		run_linter "YAML Linter (yamllint)" yamllint -d '{extends: default, rules: {line-length: disable, document-start: disable, indentation: disable, truthy: disable, comments: disable}}' "${files[@]}"
	fi
}

lint_json() {
	log_debug "json checks"

	# Get changed JSON files early
	local files=()
	mapfile -t files < <(get_changed_files ".json")
	if [[ "${#files[@]}" -eq 0 ]]; then
		log_debug "No uncommitted JSON files, skipping JSON checks"
		return 0
	fi

	if command_exists jq; then
		log_debug "Running JSON formatter on files: ${files[*]}"
		for file in "${files[@]}"; do
			if ! jq . "$file" >"${file}.tmp" 2>/dev/null; then
				add_error "JSON Formatter (jq)" "Failed to format $file"
			else
				mv "${file}.tmp" "$file"
			fi
		done
	elif command_exists prettier; then
		run_formatter_on_files "JSON Formatter (prettier)" "prettier --write" "prettier --check" "${files[@]}"
	elif command_exists bunx; then
		run_formatter_on_files "JSON Formatter (prettier)" "bunx prettier --write" "bunx prettier --check" "${files[@]}"
	elif command_exists npx; then
		run_formatter_on_files "JSON Formatter (prettier)" "npx prettier --write" "npx prettier --check" "${files[@]}"
	fi
}

lint_shell() {
	log_debug "shell checks"

	# Get changed shell files early
	local files=()
	mapfile -t files < <(get_changed_files ".sh" ".bash")
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
		run_linter "Shell Linter (shellcheck)" shellcheck "${filtered[@]}"
	fi
	if command_exists shfmt; then
		run_formatter_on_files "Shell Formatter (shfmt)" "shfmt -w" "shfmt -d" "${filtered[@]}"
	fi
}

lint_github_actions() {
	log_debug "github actions checks"

	# Check for changed workflow files
	if ! [[ -d ".github/workflows" ]]; then
		return 0
	fi

	local files=()
	mapfile -t files < <(get_changed_files ".yaml" ".yml" | grep ".github/workflows/")
	if [[ "${#files[@]}" -eq 0 ]]; then
		log_debug "No uncommitted GitHub Actions workflow files, skipping actionlint"
		return 0
	fi

	if command_exists actionlint; then
		# actionlint doesn't support file arguments, runs on .github/workflows directory
		run_linter "GitHub Actions Linter (actionlint)" actionlint "${files[@]}"
	fi
}

lint_terraform() {
	log_debug "terraform checks"

	# Get changed Terraform files early
	local files=()
	mapfile -t files < <(get_changed_files ".tf" ".tfvars")
	if [[ "${#files[@]}" -eq 0 ]]; then
		log_debug "No uncommitted Terraform files, skipping Terraform checks"
		return 0
	fi

	if command_exists terraform; then
		log_debug "Found changed Terraform files, running terraform fmt"
		if ! terraform fmt >/dev/null 2>&1; then
			add_error "Terraform Formatter" "terraform fmt failed"
		elif ! output=$(terraform fmt -check 2>&1); then
			add_error "Terraform Formatter needs fixing" "$output"
		fi
		# Run validate if any .tf files exist in current directory
		if compgen -G "*.tf" >/dev/null 2>&1; then
			run_linter "Terraform Validator" terraform validate
		fi
	fi
	if command_exists tflint; then
		run_linter "Terraform Linter (tflint)" tflint
	fi
}

lint_markdown() {
	log_debug "markdown checks"

	# Get changed Markdown files early
	local files=()
	mapfile -t files < <(get_changed_files ".md")
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

	if command_exists prettier; then
		run_formatter_on_files "Markdown Formatter (prettier)" "prettier --write" "prettier --check" "${absolute_files[@]}"
	elif command_exists bunx; then
		run_formatter_on_files "Markdown Formatter (prettier)" "bunx prettier --write" "bunx prettier --check" "${absolute_files[@]}"
	elif command_exists npx; then
		run_formatter_on_files "Markdown Formatter (prettier)" "npx prettier --write" "npx prettier --check" "${absolute_files[@]}"
	elif command_exists mdformat; then
		run_formatter_on_files "Markdown Formatter (mdformat)" "mdformat" "mdformat --check" "${filtered_files[@]}"
	fi
	if command_exists markdownlint; then
		run_linter "Markdown Linter (markdownlint)" markdownlint --disable MD013 MD026 MD033 MD040 MD041 -- "${filtered_files[@]}"
	fi
}

# --- MAIN EXECUTION ---
[[ "$1" == "--debug" ]] && export CLAUDE_HOOKS_DEBUG=1

# Layered config: global defaults, then project overrides.
# shellcheck source=/dev/null
[[ -f "$HOME/.claude/.claude-hooks-config.sh" ]] && source "$HOME/.claude/.claude-hooks-config.sh"
# shellcheck source=/dev/null
[[ -f ".claude-hooks-config.sh" ]] && source ".claude-hooks-config.sh"

PROJECT_TYPE=$(detect_project_type)

if [[ "$PROJECT_TYPE" == "unknown" ]]; then
	log_debug "No recognized project type, skipping."
	print_summary_and_exit
fi

# Run linters based on detected types
IFS=',' read -ra types <<<"${PROJECT_TYPE#mixed:}"
for type in "${types[@]}"; do
	case "$type" in
	go) lint_go ;;
	python) lint_python ;;
	javascript) lint_javascript ;;
	yaml) lint_yaml ;;
	json) lint_json ;;
	shell) lint_shell ;;
	github_actions) lint_github_actions ;;
	terraform) lint_terraform ;;
	markdown) lint_markdown ;;
	esac
done

print_summary_and_exit
