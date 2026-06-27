#!/usr/bin/env bash
# Orchestrator: loads lib + language modules, detects project type, dispatches linters.

set -o pipefail
set +e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=lib.sh
source "$SCRIPT_DIR/lib.sh"

# --- MAIN EXECUTION ---
[[ "$1" == "--debug" ]] && export CLAUDE_HOOKS_DEBUG=1
init_hook_input
record_hook_edited_files

# Layered config: global defaults, then project overrides.
# shellcheck source=/dev/null
[[ -f "$HOME/.claude/.claude-hooks-config.sh" ]] && source "$HOME/.claude/.claude-hooks-config.sh"
# shellcheck source=/dev/null
[[ -f ".claude-hooks-config.sh" ]] && source ".claude-hooks-config.sh"

# --- SKIP CHECK ---
# Skip linting via env var (transient: SKIP_LINT=1 <command>)
# or via .nolint file in project root (persistent; add to .gitignore).
# Skip just the architecture-tier tools (knip, dependency-cruiser, …) via
# .nolint-arch or SKIP_ARCH=1 — fast linters still run.
if [[ "${SKIP_LINT:-}" == "1" ]] || [[ -f ".nolint" ]]; then
	echo -e "${CYAN}⏭ Linting skipped${NC}" >&2
	exit 0
fi
[[ -f ".nolint-arch" ]] && export SKIP_ARCH=1

# --- LANGUAGE MODULES ---
# shellcheck source=lint-csharp.sh
source "$SCRIPT_DIR/lint-csharp.sh"
# shellcheck source=lint-go.sh
source "$SCRIPT_DIR/lint-go.sh"
# shellcheck source=lint-python.sh
source "$SCRIPT_DIR/lint-python.sh"
# shellcheck source=lint-rust.sh
source "$SCRIPT_DIR/lint-rust.sh"
# shellcheck source=lint-typescript.sh
source "$SCRIPT_DIR/lint-typescript.sh"
# shellcheck source=lint-web.sh
source "$SCRIPT_DIR/lint-web.sh"
# shellcheck source=lint-shell.sh
source "$SCRIPT_DIR/lint-shell.sh"

# --- PROJECT DETECTION ---
detect_project_type() {
	local project_type="unknown"
	local types=()

	# C# /.NET project
	if [[ -f "global.json" ]] || [[ -n "$(find . -maxdepth 4 \( -name "*.cs" -o -name "*.csproj" -o -name "*.sln" -o -name "*.props" -o -name "*.targets" \) -type f -print -quit 2>/dev/null)" ]]; then
		types+=("csharp")
	fi
	# Go project
	if [[ -f "go.mod" ]] || [[ -f "go.sum" ]] || [[ -n "$(find . -maxdepth 3 -name "*.go" -type f -print -quit 2>/dev/null)" ]]; then
		types+=("go")
	fi
	# Python project
	if [[ -f "pyproject.toml" ]] || [[ -f "setup.py" ]] || [[ -f "requirements.txt" ]] || [[ -n "$(find . -maxdepth 3 -name "*.py" -type f -print -quit 2>/dev/null)" ]]; then
		types+=("python")
	fi
	# Rust project
	if [[ -f "Cargo.toml" ]] || [[ -f "Cargo.lock" ]] || [[ -n "$(find . -maxdepth 4 \( -name "Cargo.toml" -o -name "*.rs" \) -type f -print -quit 2>/dev/null)" ]]; then
		types+=("rust")
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

PROJECT_TYPE=$(detect_project_type)

if [[ "$PROJECT_TYPE" == "unknown" ]]; then
	log_debug "No recognized project type, skipping."
	print_summary_and_exit
fi

# Run linters based on detected types
IFS=',' read -ra types <<<"${PROJECT_TYPE#mixed:}"
for type in "${types[@]}"; do
	case "$type" in
	csharp) lint_csharp ;;
	go) lint_go ;;
	python) lint_python ;;
	rust) lint_rust ;;
	javascript) lint_typescript ;;
	yaml) lint_yaml ;;
	json) lint_json ;;
	shell) lint_shell ;;
	github_actions) lint_github_actions ;;
	terraform) lint_terraform ;;
	markdown) lint_markdown ;;
	esac
done

run_lint_fallbacks
print_summary_and_exit
