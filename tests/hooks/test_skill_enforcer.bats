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

@test "skill-enforcer: Rust cargo work routes to writing-rust" {
	run bash "$HOOK" <<<'{"prompt":"fix the Rust borrow checker error in src/lib.rs and run cargo test"}'
	[ "$status" -eq 0 ]
	[[ "$output" == *"writing-rust"* ]]
}

@test "skill-enforcer: C# dotnet work routes to writing-csharp" {
	run bash "$HOOK" <<<'{"prompt":"fix the nullable warning in src/Foo/Bar.cs and run dotnet test"}'
	[ "$status" -eq 0 ]
	[[ "$output" == *"writing-csharp"* ]]
}

@test "skill-enforcer: Java Gradle work routes to writing-java-kotlin" {
	run bash "$HOOK" <<<'{"prompt":"fix the failing JUnit test in src/main/java/com/acme/App.java and run gradle test"}'
	[ "$status" -eq 0 ]
	[[ "$output" == *"writing-java-kotlin"* ]]
}

@test "skill-enforcer: Kotlin ktlint work routes to writing-java-kotlin" {
	run bash "$HOOK" <<<'{"prompt":"format the Ktor route in src/main/kotlin/App.kt with ktlint"}'
	[ "$status" -eq 0 ]
	[[ "$output" == *"writing-java-kotlin"* ]]
}

@test "skill-enforcer: JavaScript does not route to writing-java-kotlin" {
	run bash "$HOOK" <<<'{"prompt":"fix this JavaScript file src/app.js and run npm test"}'
	[ "$status" -eq 0 ]
	[[ "$output" != *"writing-java-kotlin"* ]]
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

@test "skill-enforcer: Slack channel is not Go development" {
	run bash "$HOOK" <<<'{"prompt":"Which Slack channel should I use for this question?"}'
	[ "$status" -eq 0 ]
	[[ "$output" != *"writing-go"* ]]
}

@test "skill-enforcer: JavaScript async await is not Python development" {
	run bash "$HOOK" <<<'{"prompt":"Please explain the difference between async and await in JavaScript."}'
	[ "$status" -eq 0 ]
	[[ "$output" != *"writing-python"* ]]
}

@test "skill-enforcer: explicit Go and Python still route" {
	run bash "$HOOK" <<<'{"prompt":"Implement a channel in Go and a Python asyncio worker."}'
	[ "$status" -eq 0 ]
	[[ "$output" == *"writing-go"* ]]
	[[ "$output" == *"writing-python"* ]]
}

@test "skill-enforcer: ordinary planning and procedural steps do not request reasoning format" {
	run bash "$HOOK" <<<'{"prompt":"Plan this out: write a step-by-step installation guide."}'
	[ "$status" -eq 0 ]
	[[ "$output" != *"sequential-thinking"* ]]
}

@test "skill-enforcer: explicit stepwise thinking request routes" {
	run bash "$HOOK" <<<'{"prompt":"Think step by step about the competing constraints."}'
	[ "$status" -eq 0 ]
	[[ "$output" == *"sequential-thinking"* ]]
}

@test "skill-enforcer: disabled native hook is silent" {
	run env HOOK_SKILL_ENFORCER=0 bash "$HOOK" <<<'{"prompt":"Implement the Python worker and run pytest."}'
	[ "$status" -eq 0 ]
	[ -z "$output" ]
}

@test "skill-enforcer: disabled Pi hook preserves allow protocol" {
	run env HOOK_SKILL_ENFORCER=0 bash "$HOOK" <<<'{"event":"prompt-submit","piEvent":{"prompt":"Implement the Python worker and run pytest."}}'
	[ "$status" -eq 0 ]
	[ "$output" = '{"decision":"allow"}' ]
}

@test "skill-enforcer: Pi suggestions use stderr and stdout remains a decision" {
	bats_require_minimum_version 1.5.0
	run --separate-stderr bash "$HOOK" <<<'{"event":"prompt-submit","piEvent":{"prompt":"Implement the Python worker and run pytest."}}'
	[ "$status" -eq 0 ]
	[ "$output" = '{"decision":"allow"}' ]
	[[ "$stderr" == *"writing-python"* ]]
}

@test "skill-enforcer: cargo test does not match go test" {
	run bash "$HOOK" <<<'{"prompt":"Implement the Rust parser in lib.rs and run cargo test."}'
	[ "$status" -eq 0 ]
	[[ "$output" == *"writing-rust"* ]]
	[[ "$output" != *"writing-go"* ]]
}

@test "skill-enforcer: Python type hints do not match ts abbreviation" {
	run bash "$HOOK" <<<'{"prompt":"Implement validation in parser.py with Python type hints."}'
	[ "$status" -eq 0 ]
	[[ "$output" == *"writing-python"* ]]
	[[ "$output" != *"writing-typescript"* ]]
}

@test "skill-enforcer: ownership checklist is not Rust" {
	run bash "$HOOK" <<<'{"prompt":"Write an ownership checklist for the support team."}'
	[ "$status" -eq 0 ]
	[[ "$output" != *"writing-rust"* ]]
}

@test "skill-enforcer: explicit Rust ownership still routes" {
	run bash "$HOOK" <<<'{"prompt":"Explain Rust ownership and lifetimes for this parser."}'
	[ "$status" -eq 0 ]
	[[ "$output" == *"writing-rust"* ]]
}

@test "skill-enforcer: Slack recommendation is not web research" {
	run bash "$HOOK" <<<'{"prompt":"Which Slack channel should I use for this question?"}'
	[ "$status" -eq 0 ]
	[ -z "$output" ]
}

@test "skill-enforcer: technical recommendation still suggests research" {
	run bash "$HOOK" <<<'{"prompt":"Which framework should I use for this web API?"}'
	[ "$status" -eq 0 ]
	[[ "$output" == *"researching-web"* ]]
}
