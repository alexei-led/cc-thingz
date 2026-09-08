#!/usr/bin/env bash
# git-guardrails.sh - PreToolUse hook for dangerous git commands
#
# EXIT CODES
#   0 - Allow
#   2 - Block with message

set -euo pipefail

CONFIG_FILE="${CLAUDE_HOOK_CONFIG:-$HOME/.claude/hook-config.json}"
INPUT=$(cat)
PI_RUNTIME=0

if command -v jq >/dev/null 2>&1; then
	if echo "$INPUT" | jq -e '.event == "pre-tool" and (.piEvent | type == "object")' >/dev/null 2>&1; then
		PI_RUNTIME=1
		COMMAND=$(echo "$INPUT" | jq -r '.piEvent.input.command // ""' 2>/dev/null || echo "")
	else
		COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // ""' 2>/dev/null || echo "")
	fi
else
	COMMAND=$(printf '%s' "$INPUT" | sed -n 's/.*"command"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
fi

[[ -z "$COMMAND" ]] && exit 0

# Unwraps a single level of `bash|sh|zsh|dash -c '...'` (or `-lc`, `-ec`, etc.)
# so patterns anchored on start-of-command via `^` also match the inner
# command. Ceiling: one level only — does not recurse into nested `-c`
# invocations, `env bash -c ...`, or `eval`/encoded obfuscation. Upgrade
# trigger: a reported bypass through one of those forms.
unwrap_shell_dash_c() {
	local cmd="$1"
	if [[ "$cmd" =~ ^[[:space:]]*([A-Za-z0-9_./]*/)?(bash|sh|zsh|dash)[[:space:]]+-[A-Za-z]*c[A-Za-z]*[[:space:]]+\'(.*)\'[[:space:]]*$ ]]; then
		printf '%s' "${BASH_REMATCH[3]}"
		return 0
	fi
	if [[ "$cmd" =~ ^[[:space:]]*([A-Za-z0-9_./]*/)?(bash|sh|zsh|dash)[[:space:]]+-[A-Za-z]*c[A-Za-z]*[[:space:]]+\"(.*)\"[[:space:]]*$ ]]; then
		printf '%s' "${BASH_REMATCH[3]}"
		return 0
	fi
	return 1
}

UNWRAPPED_COMMAND=$(unwrap_shell_dash_c "$COMMAND" || true)

# Normalize ordinary argv without executing shell input. This mistake guard is
# not a shell sandbox: aliases, expansions and arbitrary wrappers are out of scope.
normalize_git_options() {
	command -v python3 >/dev/null 2>&1 || return 0
	python3 -c 'import shlex,sys
try:
    lexer=shlex.shlex(sys.stdin.read(), posix=True, punctuation_chars=";&|\n")
    lexer.whitespace_split=True
    lexer.whitespace=" \t\r"
    tokens=list(lexer)
except ValueError:
    sys.exit(0)
separators={";", "&&", "||", "|", "&", "\n"}
value_options={"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--config-env", "--super-prefix"}
flags={"--no-pager", "--paginate", "-P", "-p", "--bare", "--no-replace-objects", "--literal-pathspecs", "--glob-pathspecs", "--noglob-pathspecs", "--icase-pathspecs", "--no-optional-locks"}
for i, token in enumerate(tokens):
    if token.rsplit("/",1)[-1] != "git" or (i and tokens[i-1] not in separators):
        continue
    j=i+1
    while j < len(tokens):
        arg=tokens[j]
        if arg in value_options:
            j+=2
        elif arg in flags or any(arg.startswith(opt+"=") for opt in value_options if opt.startswith("--")) or (arg.startswith(("-C", "-c")) and len(arg)>2):
            j+=1
        else:
            break
    end=j
    while end < len(tokens) and tokens[end] not in separators:
        end+=1
    print("git "+" ".join(tokens[j:end]))
' <<<"$1"
}
NORMALIZED_COMMAND=$(normalize_git_options "${UNWRAPPED_COMMAND:-$COMMAND}" || true)

DEFAULT_BLOCK_PATTERNS=$(
	cat <<'PATTERNS'
(^|[;&|[:space:]])git[[:space:]]+reset[[:space:]]+--hard([[:space:]]|$)
(^|[;&|[:space:]])git[[:space:]]+clean[[:space:]][^;&|]*(-f|--force)
(^|[;&|[:space:]])git[[:space:]]+branch[[:space:]]+-D([[:space:]]|$)
(^|[;&|[:space:]])git[[:space:]]+checkout[[:space:]]+\.([[:space:]]|$)
(^|[;&|[:space:]])git[[:space:]]+checkout[[:space:]][^;&|]*(-f|--force)
(^|[;&|[:space:]])git[[:space:]]+switch[[:space:]][^;&|]*(-C|--force-create)
(^|[;&|[:space:]])git[[:space:]]+restore[[:space:]]+\.([[:space:]]|$)
(^|[;&|[:space:]])git[[:space:]]+restore[[:space:]][^;&|]*--source[^;&|]*[[:space:]]\.([[:space:]]|$)
(^|[;&|[:space:]])git[[:space:]]+worktree[[:space:]]+remove[[:space:]][^;&|]*(--force|-f)
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

regex_valid() {
	local rc
	[[ "" =~ $1 ]] 2>/dev/null
	rc=$?
	[[ "$rc" -ne 2 ]]
}

while IFS= read -r pattern; do
	[[ -z "$pattern" ]] && continue
	if ! regex_valid "$pattern"; then
		echo "git-guardrails: skipping invalid block pattern: $pattern" >&2
		continue
	fi
	if [[ "$ALLOW_FORCE_PUSH" == "1" && "$pattern" == *"push"* ]]; then
		continue
	fi
	if [[ "$NORMALIZED_COMMAND" =~ $pattern ]] || [[ "$COMMAND" =~ $pattern ]] || { [[ -n "$UNWRAPPED_COMMAND" ]] && [[ "$UNWRAPPED_COMMAND" =~ $pattern ]]; }; then
		message="dangerous git command: $COMMAND"
		if [[ "$PI_RUNTIME" == "1" ]]; then
			printf '{"decision":"deny","reason":%s}\n' "$(printf '%s' "$message" | jq -Rsa .)"
			exit 0
		fi
		echo "BLOCKED: $message" >&2
		echo "Pattern: $pattern" >&2
		echo "Normal git push is allowed. Force/destructive git actions require explicit human execution." >&2
		exit 2
	fi
done < <(load_patterns)

exit 0
