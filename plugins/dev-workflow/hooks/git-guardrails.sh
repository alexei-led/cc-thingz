#!/usr/bin/env bash
# git-guardrails.sh - PreToolUse hook for dangerous git commands
#
# EXIT CODES
#   0 - Allow
#   2 - Block with message

set -euo pipefail

CONFIG_FILE="${CLAUDE_HOOK_CONFIG:-$HOME/.claude/hook-config.json}"
INPUT=$(cat)

if command -v jq >/dev/null 2>&1; then
	COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // ""' 2>/dev/null || echo "")
else
	COMMAND=$(printf '%s' "$INPUT" | sed -n 's/.*"command"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
fi

[[ -z "$COMMAND" ]] && exit 0

DEFAULT_BLOCK_PATTERNS=$(
	cat <<'PATTERNS'
(^|[;&|[:space:]])git[[:space:]]+reset[[:space:]]+--hard([[:space:]]|$)
(^|[;&|[:space:]])git[[:space:]]+clean[[:space:]][^;&|]*(-f|--force)
(^|[;&|[:space:]])git[[:space:]]+branch[[:space:]]+-D([[:space:]]|$)
(^|[;&|[:space:]])git[[:space:]]+checkout[[:space:]]+\.([[:space:]]|$)
(^|[;&|[:space:]])git[[:space:]]+restore[[:space:]]+\.([[:space:]]|$)
(^|[;&|[:space:]])git[[:space:]]+push[[:space:]][^;&|]*(--force|-f)([[:space:]]|$)
PATTERNS
)

load_patterns() {
	if [[ -f "$CONFIG_FILE" ]] && command -v jq >/dev/null 2>&1; then
		local patterns
		patterns=$(jq -r '."git-guardrails".block_patterns[]? // .gitGuardrails.blockPatterns[]?' "$CONFIG_FILE" 2>/dev/null || true)
		if [[ -n "$patterns" ]]; then
			printf '%s\n' "$patterns"
			return
		fi
	fi
	printf '%s\n' "$DEFAULT_BLOCK_PATTERNS"
}

ALLOW_FORCE_PUSH=0
if [[ -f "$CONFIG_FILE" ]] && command -v jq >/dev/null 2>&1; then
	ALLOW_FORCE_PUSH=$(jq -r 'if ."git-guardrails".allow_force_push == true or .gitGuardrails.allowForcePush == true then 1 else 0 end' "$CONFIG_FILE" 2>/dev/null || echo 0)
fi

while IFS= read -r pattern; do
	[[ -z "$pattern" ]] && continue
	if [[ "$ALLOW_FORCE_PUSH" == "1" && "$pattern" == *"push"* ]]; then
		continue
	fi
	if [[ "$COMMAND" =~ $pattern ]]; then
		echo "BLOCKED: dangerous git command" >&2
		echo "Command: $COMMAND" >&2
		echo "Pattern: $pattern" >&2
		echo "Normal git push is allowed. Force/destructive git actions require explicit human execution." >&2
		exit 2
	fi
done < <(load_patterns)

exit 0
