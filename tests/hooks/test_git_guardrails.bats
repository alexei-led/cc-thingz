#!/usr/bin/env bats

HOOK="$BATS_TEST_DIRNAME/../../src/hooks/git-guardrails/hook.sh"
FIXTURES="$BATS_TEST_DIRNAME/fixtures"

@test "git-guardrails: safe git command is allowed (exits 0)" {
	run bash "$HOOK" <"$FIXTURES/git_guardrails_safe.json"
	[ "$status" -eq 0 ]
}

@test "git-guardrails: git reset --hard is blocked (exits 2)" {
	run bash "$HOOK" <"$FIXTURES/git_guardrails_dangerous.json" 2>&1
	[ "$status" -eq 2 ]
}

@test "git-guardrails: git checkout force is blocked" {
	run bash "$HOOK" <<<'{"tool_input":{"command":"git checkout -f feature"}}' 2>&1
	[ "$status" -eq 2 ]
}

@test "git-guardrails: forced worktree remove is blocked" {
	run bash "$HOOK" <<<'{"tool_input":{"command":"git worktree remove --force ../repo.worktrees/feature"}}' 2>&1
	[ "$status" -eq 2 ]
}

@test "git-guardrails: git reset --hard via bash -c double-quoted is blocked" {
	run bash "$HOOK" <<<'{"tool_input":{"command":"bash -c \"git reset --hard\""}}' 2>&1
	[ "$status" -eq 2 ]
}

@test "git-guardrails: git reset --hard via bash -c single-quoted is blocked" {
	run bash "$HOOK" <<<"{\"tool_input\":{\"command\":\"bash -c 'git reset --hard'\"}}" 2>&1
	[ "$status" -eq 2 ]
}

@test "git-guardrails: git push --force via sh -c is blocked" {
	run bash "$HOOK" <<<"{\"tool_input\":{\"command\":\"sh -c 'git push --force origin main'\"}}" 2>&1
	[ "$status" -eq 2 ]
}

@test "git-guardrails: descriptive echo mentioning git reset --hard is not blocked" {
	run bash "$HOOK" <<<'{"tool_input":{"command":"echo \"git reset --hard is dangerous\""}}' 2>&1
	[ "$status" -eq 0 ]
}
