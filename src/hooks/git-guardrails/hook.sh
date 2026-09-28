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

# Cleanup of merged work is allowed, so agents can tidy up after squash-merged
# PRs (`git branch -d` refuses those branches):
# - `git branch -D <names>` when every branch is merged into origin's default
#   branch and no worktree has it checked out;
# - `git worktree remove --force <path>` when the worktree's HEAD is merged and it
#   has no staged or unstaged changes to tracked files (untracked files go with it).
# Squash merges are detected offline by patch-id (git cherry), so fetch first;
# anything unverifiable stays blocked. Limit: the check trusts the local
# refs/remotes/origin/* refs, so an agent that deliberately rewrites them first
# can get past it — this is a mistake guard, like the rest of the hook.
HOOK_CWD=""
if command -v jq >/dev/null 2>&1; then
	HOOK_CWD=$(echo "$INPUT" | jq -r '.cwd // .piEvent.cwd // empty' 2>/dev/null || true)
fi
HOOK_CWD=${HOOK_CWD:-$PWD}

# Prints one line per cleanup invocation, fields separated by \x1f:
#   B <dir> <branch>...   for `git [-C dir] branch -D <names>`
#   W <dir> <path>        for `git [-C dir] worktree remove --force <path>`
# or "UNSAFE" when the form is anything the checks below cannot vouch for.
cleanup_targets() {
	command -v python3 >/dev/null 2>&1 || {
		echo UNSAFE
		return 0
	}
	python3 -c 'import os,shlex,sys
try:
    lexer=shlex.shlex(sys.stdin.read(), posix=True, punctuation_chars=";&|\n")
    lexer.whitespace_split=True
    lexer.whitespace=" \t\r"
    tokens=list(lexer)
except ValueError:
    print("UNSAFE"); sys.exit(0)
separators={";", "&&", "||", "|", "&", "\n"}
starts=[t for i, t in enumerate(tokens) if i == 0 or tokens[i-1] in separators]
if any(t in ("cd", "pushd", "popd") for t in starts):
    print("UNSAFE"); sys.exit(0)
# A git that is not a command start (sudo git, xargs git, env X=1 git) is not
# parsed below, so it must not ride along on the verdict for another invocation.
if any(t.rsplit("/",1)[-1] == "git" and i and tokens[i-1] not in separators for i, t in enumerate(tokens)):
    print("UNSAFE"); sys.exit(0)
sep="\x1f"
for i, token in enumerate(tokens):
    if token.rsplit("/",1)[-1] != "git" or (i and tokens[i-1] not in separators):
        continue
    j=i+1; cwd=""; unsafe=False
    while j < len(tokens) and tokens[j].startswith("-"):
        if tokens[j] == "-C" and j+1 < len(tokens):
            cwd=os.path.join(cwd, tokens[j+1]); j+=2
        elif tokens[j] in ("--no-pager", "-P"):
            j+=1
        else:
            unsafe=True; break
    end=j
    while end < len(tokens) and tokens[end] not in separators:
        end+=1
    args=tokens[j:end]
    if args[:1] == ["branch"] and "-D" in args:
        names=[a for a in args[1:] if a != "-D"]
        ok=names and not any(a.startswith("-") for a in names)
        print(sep.join(["B", cwd, " ".join(names)]) if ok and not unsafe else "UNSAFE")
    elif args[:2] == ["worktree", "remove"] and any(a in ("-f", "--force") for a in args[2:]):
        # One force only: a second one overrides a worktree lock, and a lock
        # means someone asked for the worktree to stay.
        forces=[a for a in args[2:] if a in ("-f", "--force")]
        paths=[a for a in args[2:] if a not in ("-f", "--force")]
        ok=len(forces) == 1 and len(paths) == 1 and not paths[0].startswith("-")
        print(sep.join(["W", cwd, paths[0]]) if ok and not unsafe else "UNSAFE")
' <<<"$1"
}

remote_default_branch() {
	local dir=$1 ref
	if ref=$(git -C "$dir" symbolic-ref -q refs/remotes/origin/HEAD 2>/dev/null); then
		echo "$ref"
		return 0
	fi
	for ref in refs/remotes/origin/main refs/remotes/origin/master; do
		if git -C "$dir" rev-parse --verify -q "$ref" >/dev/null; then
			echo "$ref"
			return 0
		fi
	done
	return 1
}

# True when <rev> is an ancestor of origin's default branch or was squash-merged into it.
commit_is_merged() {
	local dir=$1 rev=$2 base merge_base probe
	base=$(remote_default_branch "$dir") || return 1
	git -C "$dir" merge-base --is-ancestor "$rev" "$base" && return 0
	merge_base=$(git -C "$dir" merge-base "$base" "$rev") || return 1
	probe=$(git -C "$dir" commit-tree "$rev^{tree}" -p "$merge_base" -m guardrails-squash-probe) || return 1
	[[ $(git -C "$dir" cherry "$base" "$probe") == "-"* ]]
}

branch_is_merged() {
	local dir=$1 branch=$2 worktrees
	git -C "$dir" rev-parse --verify -q "refs/heads/$branch" >/dev/null || return 1
	worktrees=$(git -C "$dir" worktree list --porcelain) || return 1
	[[ $'\n'"$worktrees"$'\n' == *$'\n'"branch refs/heads/$branch"$'\n'* ]] && return 1
	commit_is_merged "$dir" "refs/heads/$branch"
}

worktree_is_merged() {
	local dir=$1 path=$2 changes
	[[ "$path" != /* ]] && path="$dir/$path"
	[[ -d "$path" ]] || return 1
	changes=$(git -C "$path" status --porcelain --untracked-files=no) || return 1
	[[ -z "$changes" ]] || return 1
	commit_is_merged "$path" HEAD
}

CLEANUP_VERIFIED=0
CLEANUP_TARGETS=$(cleanup_targets "${UNWRAPPED_COMMAND:-$COMMAND}" || echo UNSAFE)
if [[ -n "$CLEANUP_TARGETS" && "$CLEANUP_TARGETS" != *UNSAFE* ]]; then
	# \x1f, not a tab: read collapses leading whitespace separators, which would
	# shift an empty dir column into the next field.
	checked=0 failed=0
	while IFS=$'\x1f' read -r kind dir rest; do
		[[ -z "$dir" ]] && dir=$HOOK_CWD
		[[ "$dir" != /* ]] && dir="$HOOK_CWD/$dir"
		if [[ "$kind" == W ]]; then
			checked=$((checked + 1))
			worktree_is_merged "$dir" "$rest" 2>/dev/null || failed=1
			continue
		fi
		for name in $rest; do
			checked=$((checked + 1))
			branch_is_merged "$dir" "$name" 2>/dev/null || failed=1
		done
	done <<<"$CLEANUP_TARGETS"
	if [[ "$checked" -gt 0 && "$failed" -eq 0 ]]; then
		CLEANUP_VERIFIED=1
	fi
fi

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
	if [[ "$CLEANUP_VERIFIED" == "1" && ("$pattern" == *"branch"*"-D"* || "$pattern" == *"worktree"*"remove"*) ]]; then
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
		if [[ "$pattern" == *"branch"*"-D"* || "$pattern" == *"worktree"*"remove"* ]]; then
			echo "Cleanup of merged work is allowed: git branch -D for branches merged into origin's default branch (squash merges included) that no worktree has checked out, and git worktree remove --force for a merged worktree without tracked changes. Run git fetch first." >&2
		fi
		exit 2
	fi
done < <(load_patterns)

exit 0
