#!/usr/bin/env bash
# smart-lint.sh - concise project-aware format and lint checks.

set -o pipefail
advisory_exit() {
	local code="$?"
	trap - EXIT
	[[ "$code" -eq 0 ]] || printf 'smart-lint internal error (exit %s); checks incomplete, agent may continue\n' "$code" >&2
	if [[ "${SMART_LINT_PI_RUNTIME:-0}" == 1 ]]; then printf '{"decision":"allow"}\n' >&3; fi
	exit 0
}
trap advisory_exit EXIT

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INPUT=$(cat)
export -n HOOK_INPUT_JSON
HOOK_INPUT_JSON="${INPUT:-${HOOK_INPUT_JSON:-}}"

# shellcheck source=smart-lint/main.sh
source "$SCRIPT_DIR/smart-lint/main.sh"
