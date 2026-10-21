#!/usr/bin/env bash
# smart-lint.sh - concise project-aware format and lint checks.

set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INPUT=$(cat)
export -n HOOK_INPUT_JSON
HOOK_INPUT_JSON="${INPUT:-${HOOK_INPUT_JSON:-}}"

# shellcheck source=smart-lint/main.sh
source "$SCRIPT_DIR/smart-lint/main.sh"
