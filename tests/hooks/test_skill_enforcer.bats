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

@test "skill-enforcer: known-file extraction routes to smart-explore" {
	run bash "$HOOK" <"$FIXTURES/skill_enforcer_smart_explore.json"
	[ "$status" -eq 0 ]
	[[ "$output" == *"smart-explore"* ]]
}

@test "skill-enforcer: codebase flow is left to companion workflows" {
	run bash "$HOOK" <"$FIXTURES/skill_enforcer_codebase_search.json"
	[ "$status" -eq 0 ]
	[ -z "$output" ]
}
