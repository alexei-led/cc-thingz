#!/usr/bin/env bats

HOOK="$BATS_TEST_DIRNAME/../../src/hooks/skill-enforcer/hook.sh"
FIXTURES="$BATS_TEST_DIRNAME/fixtures"

@test "skill-enforcer: unrelated prompt is silent and exits 0" {
	run bash "$HOOK" <"$FIXTURES/skill_enforcer_no_match.json"
	[ "$status" -eq 0 ]
	[ -z "$output" ]
}

@test "skill-enforcer: prompt matching known skills outputs suggestion and exits 0" {
	run bash "$HOOK" <"$FIXTURES/skill_enforcer_match.json"
	[ "$status" -eq 0 ]
	[[ "$output" == *"Consider skills"* ]]
}

@test "skill-enforcer: debate prompts route to brainstorming" {
	run bash "$HOOK" <"$FIXTURES/skill_enforcer_debate.json"
	[ "$status" -eq 0 ]
	[[ "$output" == *"brainstorming-ideas"* ]]
	[[ "$output" != *"debating"* ]]
}

@test "skill-enforcer: structural code search is left to companion workflows" {
	run bash "$HOOK" <"$FIXTURES/skill_enforcer_ast_grep.json"
	[ "$status" -eq 0 ]
	[ -z "$output" ]
}

@test "skill-enforcer: shell scripting routes to writing-shell" {
	run bash "$HOOK" <"$FIXTURES/skill_enforcer_shell.json"
	[ "$status" -eq 0 ]
	[[ "$output" == *"writing-shell"* ]]
}

@test "skill-enforcer: codebase flow is left to companion workflows" {
	run bash "$HOOK" <"$FIXTURES/skill_enforcer_codebase_search.json"
	[ "$status" -eq 0 ]
	[ -z "$output" ]
}

@test "skill-enforcer: commit prompt routes to committing-code" {
	run bash "$HOOK" <<<'{"prompt":"commit these changes as two logical commits"}'
	[ "$status" -eq 0 ]
	[[ "$output" == *"committing-code"* ]]
}

@test "skill-enforcer: delete merged branches routes to cleanup-git" {
	run bash "$HOOK" <<<'{"prompt":"delete merged branches and stale worktrees"}'
	[ "$status" -eq 0 ]
	[[ "$output" == *"cleanup-git"* ]]
}

@test "skill-enforcer: pre-commit gitleaks setup routes to configuring-git-hygiene" {
	run bash "$HOOK" <<<'{"prompt":"setup pre-commit hooks with gitleaks"}'
	[ "$status" -eq 0 ]
	[[ "$output" == *"configuring-git-hygiene"* ]]
	[[ "$output" != *"configuring-git-flow"* ]]
}

@test "skill-enforcer: isolated branch routes to using-git-worktrees" {
	run bash "$HOOK" <<<'{"prompt":"create a new isolated branch for feature auth"}'
	[ "$status" -eq 0 ]
	[[ "$output" == *"using-git-worktrees"* ]]
}

@test "skill-enforcer: instruction review routes to reviewing-instructions" {
	run bash "$HOOK" <<<'{"prompt":"review all git-flow skills for instruction quality"}'
	[ "$status" -eq 0 ]
	[[ "$output" == *"reviewing-instructions"* ]]
}
