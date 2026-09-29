#!/usr/bin/env bash
# git-guardrails.sh - PreToolUse hook for dangerous git commands
#
# EXIT CODES
#   0 - Allow
#   2 - Block with message
#
# All detection lives in decide.py (passed as $1, the packaged path to it):
# a single python3 process tokenizes the command with shlex and evaluates
# each git invocation's argv directly against a destructive-op table,
# rather than matching a regex across every statement joined together.
# This script only extracts the command/config from the hook payload, runs
# a zero-fork fast path for the common case of a non-git command, and
# translates decide.py's verdict into this hook's exit code / Pi JSON
# contract.

set -euo pipefail

CONFIG_FILE="${CLAUDE_HOOK_CONFIG:-$HOME/.claude/hook-config.json}"
DECIDE_PY="$1"
IFS= read -r -d '' INPUT || true

# Fast path, on the raw hook payload, before any fork at all (no jq, no
# python3): most Bash calls aren't git at all (ls, cat, npm test, ...).
# Quoting or backslash-escaping can spell "git" without the literal
# substring appearing (g\it, g""it, g'i't all become git once the shell
# parses them), so this tests a copy of the raw payload with \, ', and "
# removed - JSON's own quoting only adds more of those same characters,
# so stripping them can only reveal a "git" word, never hide one. The
# real $COMMAND, extracted below with its real quoting intact, is what
# decide.py's tokenizer actually parses. A "git" mentioned only inside a
# heredoc body or a quoted string still reaches the slow path (harmless:
# decide.py strips heredocs and treats quoted text as data, not
# commands), so this check only has to be safe to say no on, not
# exhaustive. Limit: a payload that JSON-escapes a letter of "git" as \u00XX
# skips the check; harnesses only escape control characters.
# No word-boundary test: JSON escapes like \n before "git" become "ngit"
# once backslashes are stripped, so any "git" substring takes the slow path.
UNQUOTED_FOR_SCAN=${INPUT//[\\\"\']/}
if [[ "$UNQUOTED_FOR_SCAN" != *git* ]]; then
	exit 0
fi

PI_RUNTIME=0
COMMAND=""
HOOK_CWD=""

if command -v jq >/dev/null 2>&1; then
	# One jq call for the whole input. Fields are NUL-separated because the
	# command itself may span lines; splitting on newlines would analyze only
	# its first line. `read -d ''` also works in bash 3.2, which stock macOS ships.
	{
		IFS= read -r -d '' PI_RUNTIME || true
		IFS= read -r -d '' COMMAND || true
		IFS= read -r -d '' HOOK_CWD || true
	} < <(
		printf '%s' "$INPUT" | jq -j '
			if .event == "pre-tool" and (.piEvent | type == "object") then
				["1", (.piEvent.input.command // ""), (.piEvent.cwd // .vendorEvent.cwd // .cwd // "")]
			else
				["0", (.tool_input.command // ""), (.cwd // .vendorEvent.cwd // "")]
			end
			| map(tostring + "\u0000") | add
		' 2>/dev/null || true
	)
	PI_RUNTIME=${PI_RUNTIME:-0}
else
	COMMAND=$(printf '%s' "$INPUT" | sed -n 's/.*"command"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
fi
HOOK_CWD=${HOOK_CWD:-$PWD}

[[ -z "$COMMAND" ]] && exit 0

deny() {
	local rule=$1 cleanup_hint=$2
	local message="dangerous git command: $COMMAND"
	if [[ "$PI_RUNTIME" == "1" ]]; then
		printf '{"decision":"deny","reason":%s}\n' \
			"$(printf '%s\nPattern: %s' "$message" "$rule" | jq -Rsa .)"
		exit 0
	fi
	echo "BLOCKED: $message" >&2
	echo "Pattern: $rule" >&2
	echo "Normal git push is allowed. Force/destructive git actions require explicit human execution." >&2
	if [[ "$cleanup_hint" == "1" ]]; then
		echo "Cleanup of merged work is allowed: git branch -D for branches merged into origin's default branch (squash merges included) that no worktree has checked out, and git worktree remove --force for a merged worktree without tracked changes. Run git fetch first." >&2
	fi
	exit 2
}

if ! command -v python3 >/dev/null 2>&1; then
	deny "python3 is required to safely analyze git commands" 0
fi

ALLOW_FORCE_PUSH=0
PATTERNS=""
if [[ -f "$CONFIG_FILE" ]] && command -v jq >/dev/null 2>&1; then
	CONFIG_JQ=$(
		jq -r '
			(if ."git-guardrails".allow_force_push == true or .gitGuardrails.allowForcePush == true then "1" else "0" end),
			(."git-guardrails".block_patterns[]? // .gitGuardrails.blockPatterns[]? // empty)
		' "$CONFIG_FILE" 2>/dev/null || true
	)
	if [[ -n "$CONFIG_JQ" ]]; then
		# First line is the flag, the rest are patterns (one per line).
		ALLOW_FORCE_PUSH=${CONFIG_JQ%%$'\n'*}
		PATTERNS=""
		[[ "$CONFIG_JQ" == *$'\n'* ]] && PATTERNS=${CONFIG_JQ#*$'\n'}
	fi
fi

set +e
DECISION=$(GG_COMMAND="$COMMAND" GG_CWD="$HOOK_CWD" GG_ALLOW_FORCE_PUSH="$ALLOW_FORCE_PUSH" GG_PATTERNS="$PATTERNS" python3 "$DECIDE_PY")
DECIDE_STATUS=$?
set -e

{
	IFS= read -r VERDICT || true
	IFS= read -r RULE || true
	IFS= read -r CLEANUP_HINT || true
} <<<"$DECISION"

if [[ "$DECIDE_STATUS" -ne 0 || "$VERDICT" != "ALLOW" ]]; then
	if [[ "$VERDICT" == "BLOCK" ]]; then
		deny "$RULE" "$CLEANUP_HINT"
	fi
	deny "decide.py failed unexpectedly" 0
fi

exit 0
