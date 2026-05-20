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

@test "skill-enforcer: structural code search routes to existing search skills" {
	run bash "$HOOK" <"$FIXTURES/skill_enforcer_ast_grep.json"
	[ "$status" -eq 0 ]
	[[ "$output" == *"searching-code"* ]]
	[[ "$output" == *"using-modern-cli"* ]]
	[[ "$output" != *"ast-grep "* ]]
	[[ "$output" != *"smart-explore"* ]]
}

@test "skill-enforcer: known-file extraction routes to smart-explore" {
	run bash "$HOOK" <"$FIXTURES/skill_enforcer_smart_explore.json"
	[ "$status" -eq 0 ]
	[[ "$output" == *"smart-explore"* ]]
	[[ "$output" != *"searching-code"* ]]
}

@test "skill-enforcer: codebase flow routes to searching-code not smart-explore" {
	run bash "$HOOK" <"$FIXTURES/skill_enforcer_codebase_search.json"
	[ "$status" -eq 0 ]
	[[ "$output" == *"searching-code"* ]]
	[[ "$output" != *"smart-explore"* ]]
}
