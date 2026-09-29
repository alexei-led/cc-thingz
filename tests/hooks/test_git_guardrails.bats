#!/usr/bin/env bats

HOOK="$BATS_TEST_DIRNAME/../../src/hooks/git-guardrails/hook.sh"
DECIDE="$BATS_TEST_DIRNAME/../../src/hooks/git-guardrails/decide.py"
FIXTURES="$BATS_TEST_DIRNAME/fixtures"

@test "git-guardrails: safe git command is allowed (exits 0)" {
	run bash "$HOOK" "$DECIDE" <"$FIXTURES/git_guardrails_safe.json"
	[ "$status" -eq 0 ]
}

@test "git-guardrails: non-git command is allowed without forking python3" {
	run bash "$HOOK" "/nonexistent/decide.py" <<<'{"tool_input":{"command":"ls -la"}}'
	[ "$status" -eq 0 ]
}

@test "git-guardrails: git reset --hard is blocked (exits 2)" {
	run bash "$HOOK" "$DECIDE" <"$FIXTURES/git_guardrails_dangerous.json" 2>&1
	[ "$status" -eq 2 ]
}

@test "git-guardrails: git checkout force is blocked" {
	run bash "$HOOK" "$DECIDE" <<<'{"tool_input":{"command":"git checkout -f feature"}}' 2>&1
	[ "$status" -eq 2 ]
}

@test "git-guardrails: forced worktree remove is blocked" {
	run bash "$HOOK" "$DECIDE" <<<'{"tool_input":{"command":"git worktree remove --force ../repo.worktrees/feature"}}' 2>&1
	[ "$status" -eq 2 ]
}

@test "git-guardrails: worktree remove without force is allowed" {
	run bash "$HOOK" "$DECIDE" <<<'{"tool_input":{"command":"git worktree remove ../fix-foo"}}'
	[ "$status" -eq 0 ]
}

@test "git-guardrails: git reset --hard via bash -c double-quoted is blocked" {
	run bash "$HOOK" "$DECIDE" <<<'{"tool_input":{"command":"bash -c \"git reset --hard\""}}' 2>&1
	[ "$status" -eq 2 ]
}

@test "git-guardrails: git reset --hard via bash -c single-quoted is blocked" {
	run bash "$HOOK" "$DECIDE" <<<"{\"tool_input\":{\"command\":\"bash -c 'git reset --hard'\"}}" 2>&1
	[ "$status" -eq 2 ]
}

@test "git-guardrails: git push --force via sh -c is blocked" {
	run bash "$HOOK" "$DECIDE" <<<"{\"tool_input\":{\"command\":\"sh -c 'git push --force origin main'\"}}" 2>&1
	[ "$status" -eq 2 ]
}

@test "git-guardrails: descriptive echo mentioning git reset --hard is not blocked" {
	run bash "$HOOK" "$DECIDE" <<<'{"tool_input":{"command":"echo \"git reset --hard is dangerous\""}}' 2>&1
	[ "$status" -eq 0 ]
}

@test "git-guardrails: heredoc body mentioning git reset --hard is not blocked" {
	run bash "$HOOK" "$DECIDE" <<<'{"tool_input":{"command":"cat <<'"'"'EOF'"'"'\nnever run git reset --hard on main\nEOF\n"}}' 2>&1
	[ "$status" -eq 0 ]
}

@test "git-guardrails: commit message mentioning git push --force is not blocked" {
	run bash "$HOOK" "$DECIDE" <<<'{"tool_input":{"command":"git commit -m \"docs: never run git push --force\""}}' 2>&1
	[ "$status" -eq 0 ]
}

@test "git-guardrails: global options cannot hide reset" {
	run bash "$HOOK" "$DECIDE" <<<'{"tool_input":{"command":"git -C \"/tmp/my repo\" -c core.pager=cat --no-pager reset --hard"}}'
	[ "$status" -eq 2 ]
}

@test "git-guardrails: Pi global options return deny envelope" {
	run bash "$HOOK" "$DECIDE" <<<'{"event":"pre-tool","piEvent":{"input":{"command":"git --git-dir=/tmp/repo/.git --work-tree /tmp/repo push --force"}}}'
	[ "$status" -eq 0 ]
	[[ "$output" == *'"decision":"deny"'* ]]
}

@test "git-guardrails: Pi cwd falls back to vendorEvent.cwd" {
	run bash "$HOOK" "$DECIDE" <<<'{"event":"pre-tool","piEvent":{"input":{"command":"git status"}},"vendorEvent":{"cwd":"/tmp"}}'
	[ "$status" -eq 0 ]
}

@test "git-guardrails: ordinary inspection with global options allowed" {
	run bash "$HOOK" "$DECIDE" <<<'{"tool_input":{"command":"git -C /tmp/repo --no-pager diff --stat"}}'
	[ "$status" -eq 0 ]
}

@test "git-guardrails: pull --ff-only after checkout in one line is allowed" {
	run bash "$HOOK" "$DECIDE" <<<'{"tool_input":{"command":"git checkout main && git pull --ff-only"}}'
	[ "$status" -eq 0 ]
}

@test "git-guardrails: worktree remove then fetch and ff-only merge is allowed" {
	run bash "$HOOK" "$DECIDE" <<<'{"tool_input":{"command":"git worktree remove ../wt 2>/dev/null; git fetch && git merge --ff-only"}}'
	[ "$status" -eq 0 ]
}

@test "git-guardrails: sudo-prefixed clean is blocked" {
	run bash "$HOOK" "$DECIDE" <<<'{"tool_input":{"command":"sudo git clean -fdx"}}'
	[ "$status" -eq 2 ]
}

@test "git-guardrails: VAR=value prefixed force push is blocked" {
	run bash "$HOOK" "$DECIDE" <<<'{"tool_input":{"command":"GIT_SSH_COMMAND=x git push --force"}}'
	[ "$status" -eq 2 ]
}

@test "git-guardrails: VAR=value prefixed ordinary push is allowed" {
	run bash "$HOOK" "$DECIDE" <<<'{"tool_input":{"command":"GIT_SSH_COMMAND=\"ssh -o ServerAliveInterval=20\" git push -q -u origin HEAD"}}'
	[ "$status" -eq 0 ]
}

@test "git-guardrails: push refspec force is blocked" {
	run bash "$HOOK" "$DECIDE" <<<'{"tool_input":{"command":"git push origin +main"}}'
	[ "$status" -eq 2 ]
}
