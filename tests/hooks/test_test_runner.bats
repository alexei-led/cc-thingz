#!/usr/bin/env bats

HOOK="$BATS_TEST_DIRNAME/../../src/hooks/test-runner/hook.sh"

setup() {
	unset PI_SUBAGENT_CHILD
	WORK_DIR="${BATS_TEST_TMPDIR:-$(mktemp -d)}"
	mkdir -p "$WORK_DIR"
	cd "$WORK_DIR" || exit
	git init -q
	git config user.email test@example.com
	git config user.name Test
}

teardown() {
	rm -rf "$WORK_DIR"
}

write_state() {
	local session_id="$1"
	shift
	local state_path scope
	scope=$(git rev-parse --show-prefix)
	state_path=$(git rev-parse --git-path "cc-thingz/hooks-v2/${scope}hook-files-$session_id")
	mkdir -p "$(dirname "$state_path")"
	printf '%s\n' "$@" >"$state_path"
}

assert_js_args() {
	local file="$1" kind="$2" expected="$3" flag
	case "$kind" in
	vitest) flag='--reporter=json --outputFile=' ;;
	jest) flag='--json --outputFile=' ;;
	bun) flag='--reporter=junit --reporter-outfile=' ;;
	esac
	[[ "$(cat "$file")" == "$expected $flag"* ]]
}

@test "test-runner: fast test command does not wait for watchdog budget" {
	mkdir -p bin pkg tests
	cat >pyproject.toml <<'TOML'
[project]
name = "demo"
version = "0.0.0"
[project.optional-dependencies]
test = ["pytest"]
TOML
	touch pkg/foo.py tests/test_foo.py
	cat >bin/uv <<'SH'
#!/usr/bin/env bash
exit 0
SH
	chmod +x bin/uv
	write_state s_watchdog pkg/foo.py

	start=$SECONDS
	run env PATH="$WORK_DIR/bin:$PATH" TEST_RUNNER_TIMEOUT_SECS=12 HOOK_INPUT_JSON="{\"session_id\":\"s_watchdog\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	elapsed=$((SECONDS - start))
	[ "$status" -eq 0 ]
	[ "$elapsed" -lt 8 ]
}

@test "test-runner: maps Python source file to focused pytest file" {
	mkdir -p bin pkg tests
	cat >pyproject.toml <<'TOML'
[project]
name = "demo"
version = "0.0.0"

[project.optional-dependencies]
test = ["pytest"]
TOML
	touch pkg/foo.py tests/test_foo.py
	cat >bin/uv <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >"$PWD/uv.args"
SH
	chmod +x bin/uv
	write_state s1 pkg/foo.py

	run env PATH="$WORK_DIR/bin:$PATH" HOOK_INPUT_JSON="{\"session_id\":\"s1\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ "$(cat uv.args)" = "run --extra test pytest -q --maxfail=1 --tb=short tests/test_foo.py" ]
}

@test "test-runner: indexes Python candidates once for multiple changed sources" {
	mkdir -p bin pkg tests
	cat >pyproject.toml <<'TOML'
[project]
name = "demo"
version = "0.0.0"
[project.optional-dependencies]
test = ["pytest"]
TOML
	touch pkg/foo.py pkg/bar.py tests/test_foo.py tests/test_bar.py
	cat >bin/uv <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >"$PWD/uv.args"
SH
	chmod +x bin/uv
	write_state s_multi pkg/foo.py pkg/bar.py

	run env PATH="$WORK_DIR/bin:$PATH" HOOK_INPUT_JSON="{\"session_id\":\"s_multi\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ "$(cat uv.args)" = "run --extra test pytest -q --maxfail=1 --tb=short tests/test_bar.py tests/test_foo.py" ]
}

@test "test-runner: uses uv dependency group for pytest" {
	mkdir -p bin pkg tests
	cat >pyproject.toml <<'TOML'
[project]
name = "demo"
version = "0.0.0"

[dependency-groups]
test = ["pytest"]
TOML
	touch pkg/foo.py tests/test_foo.py
	cat >bin/uv <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >"$PWD/uv.args"
SH
	chmod +x bin/uv
	write_state s_group pkg/foo.py

	run env PATH="$WORK_DIR/bin:$PATH" HOOK_INPUT_JSON="{\"session_id\":\"s_group\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ "$(cat uv.args)" = "run --group test pytest -q --maxfail=1 --tb=short tests/test_foo.py" ]
}

@test "test-runner: skips uv when pyproject does not declare pytest" {
	mkdir -p bin .venv/bin pkg tests
	cat >pyproject.toml <<'TOML'
[project]
name = "demo"
version = "0.0.0"
TOML
	touch pkg/foo.py tests/test_foo.py
	cat >bin/uv <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >"$PWD/uv.args"
exit 99
SH
	cat >.venv/bin/pytest <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >"$PWD/pytest.args"
SH
	chmod +x bin/uv .venv/bin/pytest
	write_state s_no_pytest_dep pkg/foo.py

	run env PATH="$WORK_DIR/bin:$PATH" HOOK_INPUT_JSON="{\"session_id\":\"s_no_pytest_dep\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ ! -f uv.args ]
	[ "$(cat pytest.args)" = "-q --maxfail=1 --tb=short tests/test_foo.py" ]
}

@test "test-runner: falls back when declared uv pytest is unusable" {
	mkdir -p bin .venv/bin pkg tests
	cat >pyproject.toml <<'TOML'
[project]
name = "demo"
version = "0.0.0"

[project.optional-dependencies]
test = ["pytest"]
TOML
	touch pkg/foo.py tests/test_foo.py
	cat >bin/uv <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >"$PWD/uv.args"
exit 99
SH
	cat >.venv/bin/pytest <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >"$PWD/pytest.args"
SH
	chmod +x bin/uv .venv/bin/pytest
	write_state s_broken_uv pkg/foo.py

	run env PATH="$WORK_DIR/bin:$PATH" HOOK_INPUT_JSON="{\"session_id\":\"s_broken_uv\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ "$(cat uv.args)" = "run --extra test python -c import pytest" ]
	[ "$(cat pytest.args)" = "-q --maxfail=1 --tb=short tests/test_foo.py" ]
}

@test "test-runner: reports focused test failure without blocking" {
	mkdir -p bin pkg tests
	cat >pyproject.toml <<'TOML'
[project]
name = "demo"
version = "0.0.0"

[project.optional-dependencies]
test = ["pytest"]
TOML
	touch pkg/foo.py tests/test_foo.py
	cat >bin/uv <<'SH'
#!/usr/bin/env bash
case "$*" in
*" pytest "*) echo focused-failure; exit 1 ;;
*) exit 0 ;;
esac
SH
	chmod +x bin/uv
	write_state s_fail pkg/foo.py

	run env PATH="$WORK_DIR/bin:$PATH" HOOK_INPUT_JSON="{\"session_id\":\"s_fail\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[[ "$output" == *"focused-failure"* ]]
}

@test "test-runner: subagent child without hook state skips git diff fallback" {
	mkdir -p pkg
	touch pkg/foo.py
	echo '# changed' >>pkg/foo.py

	run env PI_SUBAGENT_CHILD=1 HOOK_INPUT_JSON="{\"session_id\":\"s_child\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ -z "$output" ]
}

@test "test-runner: uses nearest non-root Makefile target as fallback" {
	mkdir -p setup/files
	touch setup/files/foo.py
	cat >setup/Makefile <<'MAKE'
test:
	@echo setup-test > ../make.marker
MAKE
	write_state s2 setup/files/foo.py

	run env HOOK_PROJECT_FALLBACK=1 HOOK_INPUT_JSON="{\"session_id\":\"s2\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ "$(cat make.marker)" = "setup-test" ]
}

@test "test-runner: nested Makefile handles files before language runners" {
	mkdir -p bin setup/files
	touch setup/files/foo.go
	cat >setup/Makefile <<'MAKE'
test:
	@echo setup-test > ../make.marker
MAKE
	cat >bin/go <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >"$PWD/go.args"
exit 1
SH
	chmod +x bin/go
	write_state s_make_first setup/files/foo.go

	run env HOOK_PROJECT_FALLBACK=1 PATH="$WORK_DIR/bin:/usr/bin:/bin" HOOK_INPUT_JSON="{\"session_id\":\"s_make_first\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ "$(cat make.marker)" = "setup-test" ]
	[ ! -f go.args ]
}

@test "test-runner: uncovered focus files still run language tests when a sibling file is covered by a nearby Makefile" {
	mkdir -p bin setup/files pkg tests
	touch setup/files/foo.go pkg/foo.py tests/test_foo.py
	cat >setup/Makefile <<'MAKE'
test:
	@echo setup-test > ../make.marker
MAKE
	cat >pyproject.toml <<'TOML'
[project]
name = "demo"
version = "0.0.0"

[project.optional-dependencies]
test = ["pytest"]
TOML
	cat >bin/uv <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >"$PWD/uv.args"
SH
	chmod +x bin/uv
	write_state s_mixed setup/files/foo.go pkg/foo.py

	run env HOOK_PROJECT_FALLBACK=1 PATH="$WORK_DIR/bin:/usr/bin:/bin" HOOK_INPUT_JSON="{\"session_id\":\"s_mixed\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ "$(cat make.marker)" = "setup-test" ]
	[[ "$(cat uv.args)" == *"tests/test_foo.py"* ]]
}

@test "test-runner: skips root Makefile fallback" {
	mkdir -p pkg
	touch pkg/foo.py
	cat >Makefile <<'MAKE'
test:
	@echo root-test > make.marker
MAKE
	write_state s3 pkg/foo.py

	run env HOOK_INPUT_JSON="{\"session_id\":\"s3\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ ! -f make.marker ]
}

@test "test-runner: TEST_RUNNER_FULL allows explicit project-wide tests" {
	cat >Makefile <<'MAKE'
test:
	@echo root-test > make.marker
MAKE

	run env TEST_RUNNER_FULL=1 HOOK_INPUT_JSON="{\"session_id\":\"s4\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ "$(cat make.marker)" = "root-test" ]
}

@test "test-runner: TEST_RUNNER_FULL uses uv pytest extra" {
	mkdir -p bin
	cat >pyproject.toml <<'TOML'
[project]
name = "demo"
version = "0.0.0"

[project.optional-dependencies]
test = ["pytest"]
TOML
	cat >bin/uv <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >"$PWD/uv.args"
SH
	chmod +x bin/uv

	run env PATH="$WORK_DIR/bin:$PATH" TEST_RUNNER_FULL=1 HOOK_INPUT_JSON="{\"session_id\":\"s_full_uv\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ "$(cat uv.args)" = "run --extra test pytest -q --maxfail=1 --tb=short" ]
}

@test "test-runner: TEST_RUNNER_FULL tolerates pytest exit 5" {
	mkdir -p bin
	cat >pyproject.toml <<'TOML'
[project]
name = "demo"
version = "0.0.0"

[project.optional-dependencies]
test = ["pytest"]
TOML
	cat >bin/uv <<'SH'
#!/usr/bin/env bash
case "$*" in
*" pytest "*) echo "no tests ran in 0.01s"; exit 5 ;;
*) exit 0 ;;
esac
SH
	chmod +x bin/uv

	run env PATH="$WORK_DIR/bin:$PATH" TEST_RUNNER_FULL=1 HOOK_INPUT_JSON="{\"session_id\":\"s_full_exit5\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
}

@test "test-runner: TEST_RUNNER_FULL uses yarn package test script" {
	mkdir -p bin
	cat >package.json <<'JSON'
{"scripts":{"test":"echo test"}}
JSON
	touch yarn.lock
	cat >bin/yarn <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >"$PWD/yarn.args"
SH
	chmod +x bin/yarn

	run env PATH="$WORK_DIR/bin:/usr/bin:/bin" TEST_RUNNER_FULL=1 HOOK_INPUT_JSON="{\"session_id\":\"s_full_yarn\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ "$(cat yarn.args)" = "run test" ]
}

@test "test-runner: TEST_RUNNER_FULL runs Vitest when no package script exists" {
	mkdir -p node_modules/.bin
	touch vitest.config.ts
	cat >node_modules/.bin/vitest <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >"$PWD/vitest.args"
SH
	chmod +x node_modules/.bin/vitest

	run env PATH="$WORK_DIR/node_modules/.bin:/usr/bin:/bin" TEST_RUNNER_FULL=1 HOOK_INPUT_JSON="{\"session_id\":\"s_full_vitest\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	assert_js_args vitest.args vitest "run --passWithNoTests"
}

@test "test-runner: TEST_RUNNER_FULL runs Jest when no package script exists" {
	mkdir -p node_modules/.bin
	touch jest.config.js
	cat >node_modules/.bin/jest <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >"$PWD/jest.args"
SH
	chmod +x node_modules/.bin/jest

	run env PATH="$WORK_DIR/node_modules/.bin:/usr/bin:/bin" TEST_RUNNER_FULL=1 HOOK_INPUT_JSON="{\"session_id\":\"s_full_jest\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	assert_js_args jest.args jest "--passWithNoTests"
}

@test "test-runner: TEST_RUNNER_FULL runs Bats when shell tests exist" {
	mkdir -p bin tests
	printf '%s\n' '#!/usr/bin/env bats' '@test "smoke" { true; }' >tests/test_smoke.bats
	cat >bin/bats <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >"$PWD/bats.args"
SH
	chmod +x bin/bats

	run env PATH="$WORK_DIR/bin:/usr/bin:/bin" TEST_RUNNER_FULL=1 HOOK_INPUT_JSON="{\"session_id\":\"s_full_bats\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ "$(cat bats.args)" = "tests/test_smoke.bats" ]
}

@test "test-runner: TEST_RUNNER_FULL runs Cargo tests" {
	mkdir -p bin src
	touch Cargo.toml src/lib.rs
	cat >bin/cargo <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >"$PWD/cargo.args"
SH
	chmod +x bin/cargo

	run env PATH="$WORK_DIR/bin:/usr/bin:/bin" TEST_RUNNER_FULL=1 HOOK_INPUT_JSON="{\"session_id\":\"s_full_rust\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ "$(cat cargo.args)" = "test --all-targets" ]
}

@test "test-runner: TEST_RUNNER_FULL runs dotnet test on the solution" {
	mkdir -p bin src/App
	touch App.sln src/App/App.csproj
	cat >bin/dotnet <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >"$PWD/dotnet.args"
SH
	chmod +x bin/dotnet

	run env PATH="$WORK_DIR/bin:/usr/bin:/bin" TEST_RUNNER_FULL=1 HOOK_INPUT_JSON="{\"session_id\":\"s_full_csharp\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ "$(cat dotnet.args)" = "test App.sln" ]
}

@test "test-runner: Go tests use failfast without verbose output" {
	mkdir -p bin pkg
	touch go.mod pkg/foo.go
	cat >bin/go <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >"$PWD/go.args"
SH
	chmod +x bin/go
	write_state s_go pkg/foo.go

	run env PATH="$WORK_DIR/bin:$PATH" HOOK_INPUT_JSON="{\"session_id\":\"s_go\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ "$(cat go.args)" = "test -json -failfast ./pkg" ]
}

@test "test-runner: Rust tests use nearest Cargo manifest" {
	mkdir -p bin crates/app/src
	cat >crates/app/Cargo.toml <<'TOML'
[package]
name = "app"
version = "0.1.0"
edition = "2021"
TOML
	touch crates/app/src/lib.rs
	cat >bin/cargo <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >"$PWD/cargo.args"
SH
	chmod +x bin/cargo
	write_state s_rust crates/app/src/lib.rs

	run env PATH="$WORK_DIR/bin:$PATH" HOOK_INPUT_JSON="{\"session_id\":\"s_rust\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ "$(cat cargo.args)" = "test --manifest-path crates/app/Cargo.toml --all-targets" ]
}

@test "test-runner: Cargo manifest edits trigger Rust tests" {
	mkdir -p bin src
	cat >Cargo.toml <<'TOML'
[package]
name = "app"
version = "0.1.0"
edition = "2021"
TOML
	touch src/lib.rs
	cat >bin/cargo <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >"$PWD/cargo.args"
SH
	chmod +x bin/cargo
	write_state s_rust_manifest Cargo.toml

	run env PATH="$WORK_DIR/bin:$PATH" HOOK_INPUT_JSON="{\"session_id\":\"s_rust_manifest\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ "$(cat cargo.args)" = "test --manifest-path Cargo.toml --all-targets" ]
}

@test "test-runner: C# source edits fall back to the containing solution" {
	mkdir -p bin src/App
	touch App.sln src/App/App.csproj src/App/Program.cs
	cat >bin/dotnet <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >"$PWD/dotnet.args"
SH
	chmod +x bin/dotnet
	write_state s_csharp src/App/Program.cs

	run env PATH="$WORK_DIR/bin:/usr/bin:/bin" HOOK_INPUT_JSON="{\"session_id\":\"s_csharp\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ "$(cat dotnet.args)" = "test App.sln" ]
}

@test "test-runner: C# test project edits run dotnet test on that project" {
	mkdir -p bin tests/App.Tests
	cat >tests/App.Tests/App.Tests.csproj <<'XML'
<Project>
  <PropertyGroup>
    <IsTestProject>true</IsTestProject>
  </PropertyGroup>
</Project>
XML
	cat >bin/dotnet <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >"$PWD/dotnet.args"
SH
	chmod +x bin/dotnet
	write_state s_csharp_proj tests/App.Tests/App.Tests.csproj

	run env PATH="$WORK_DIR/bin:/usr/bin:/bin" HOOK_INPUT_JSON="{\"session_id\":\"s_csharp_proj\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ "$(cat dotnet.args)" = "test tests/App.Tests/App.Tests.csproj" ]
}

@test "test-runner: C# non-test project edits prefer a same-dir test project" {
	mkdir -p bin src/App
	touch App.sln src/App/App.csproj
	cat >src/App/App.Tests.csproj <<'XML'
<Project>
  <PropertyGroup>
    <IsTestProject>true</IsTestProject>
  </PropertyGroup>
</Project>
XML
	cat >bin/dotnet <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >"$PWD/dotnet.args"
SH
	chmod +x bin/dotnet
	write_state s_csharp_same_dir src/App/App.csproj

	run env PATH="$WORK_DIR/bin:/usr/bin:/bin" HOOK_INPUT_JSON="{\"session_id\":\"s_csharp_same_dir\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ "$(cat dotnet.args)" = "test src/App/App.Tests.csproj" ]
}

@test "test-runner: Gradle Java source maps to matching test class" {
	mkdir -p app/src/main/java/com/example app/src/test/java/com/example
	touch settings.gradle.kts app/build.gradle.kts app/src/main/java/com/example/Service.java app/src/test/java/com/example/ServiceTest.java
	cat >gradlew <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >"$PWD/gradle.args"
SH
	chmod +x gradlew
	write_state s_gradle_java app/src/main/java/com/example/Service.java

	run env PATH="/usr/bin:/bin" HOOK_INPUT_JSON="{\"session_id\":\"s_gradle_java\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ "$(cat gradle.args)" = ":app:test --tests ServiceTest" ]
}

@test "test-runner: Maven Kotlin test file uses surefire class filter" {
	mkdir -p bin src/test/kotlin/com/example
	touch pom.xml src/test/kotlin/com/example/ServiceTest.kt
	cat >bin/mvn <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >"$PWD/mvn.args"
SH
	chmod +x bin/mvn
	write_state s_maven_kotlin src/test/kotlin/com/example/ServiceTest.kt

	run env PATH="$WORK_DIR/bin:/usr/bin:/bin" HOOK_INPUT_JSON="{\"session_id\":\"s_maven_kotlin\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ "$(cat mvn.args)" = "-q -f ./pom.xml -Dtest=ServiceTest test" ]
}

@test "test-runner: TEST_RUNNER_FULL runs Gradle test" {
	touch build.gradle.kts
	cat >gradlew <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >"$PWD/gradle.args"
SH
	chmod +x gradlew

	run env PATH="/usr/bin:/bin" TEST_RUNNER_FULL=1 HOOK_INPUT_JSON="{\"session_id\":\"s_full_gradle\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ "$(cat gradle.args)" = "test" ]
}

@test "test-runner: Vitest uses related for source files" {
	mkdir -p node_modules/.bin src
	touch vitest.config.ts src/foo.ts
	cat >node_modules/.bin/vitest <<'SH'
#!/usr/bin/env bash
case "$*" in
*"--passWithNoTests"*) printf '%s\n' "$*" >"$PWD/vitest.args" ;;
*) exit 1 ;;
esac
SH
	chmod +x node_modules/.bin/vitest
	write_state s_vitest src/foo.ts

	run env HOOK_INPUT_JSON="{\"session_id\":\"s_vitest\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	assert_js_args vitest.args vitest "related src/foo.ts --run --passWithNoTests"
}

@test "test-runner: Vitest treats JS support files in tests as related sources" {
	mkdir -p node_modules/.bin tests
	touch vitest.config.ts
	printf '%s\n' 'export const helper = 1' >tests/helper.ts
	cat >node_modules/.bin/vitest <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >"$PWD/vitest.args"
SH
	chmod +x node_modules/.bin/vitest
	write_state s_vitest_helper tests/helper.ts

	run env HOOK_INPUT_JSON="{\"session_id\":\"s_vitest_helper\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	assert_js_args vitest.args vitest "related tests/helper.ts --run --passWithNoTests"
}

@test "test-runner: keeps Vitest test files with test declarations as direct targets" {
	mkdir -p node_modules/.bin tests
	touch vitest.config.ts
	printf '%s\n' 'test("works", () => {})' >tests/foo.ts
	cat >node_modules/.bin/vitest <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >"$PWD/vitest.args"
SH
	chmod +x node_modules/.bin/vitest
	write_state s_vitest_direct tests/foo.ts

	run env HOOK_INPUT_JSON="{\"session_id\":\"s_vitest_direct\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	assert_js_args vitest.args vitest "run tests/foo.ts --passWithNoTests"
}

@test "test-runner: Jest uses findRelatedTests for source files" {
	mkdir -p node_modules/.bin src
	touch jest.config.js src/foo.ts
	cat >node_modules/.bin/jest <<'SH'
#!/usr/bin/env bash
case "$*" in
*"--passWithNoTests"*) printf '%s\n' "$*" >"$PWD/jest.args" ;;
*) exit 1 ;;
esac
SH
	chmod +x node_modules/.bin/jest
	write_state s_jest src/foo.ts

	run env HOOK_INPUT_JSON="{\"session_id\":\"s_jest\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	assert_js_args jest.args jest "--findRelatedTests src/foo.ts --passWithNoTests"
}

@test "test-runner: does not fall back to Bun when Vitest config exists without Vitest" {
	mkdir -p bin src
	touch vitest.config.ts bun.lock src/foo.ts
	cat >bin/bun <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >"$PWD/bun.args"
exit 1
SH
	chmod +x bin/bun
	write_state s_no_vitest src/foo.ts

	run env PATH="$WORK_DIR/bin:/usr/bin:/bin" HOOK_INPUT_JSON="{\"session_id\":\"s_no_vitest\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ ! -f bun.args ]
}

@test "test-runner: Bun focused run passes --isolate and dedupes mapped test files" {
	mkdir -p bin src tests
	touch bun.lock src/foo.ts
	cat >tests/foo.test.ts <<'TS'
test("works", () => {})
TS
	cat >bin/bun <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >"$PWD/bun.args"
SH
	chmod +x bin/bun
	# src/foo.ts (a source) maps to tests/foo.test.ts, which is also passed
	# directly as a focus file — the merged tests+mapped_tests array must not
	# invoke bun with the same test file twice.
	write_state s_bun_isolate src/foo.ts tests/foo.test.ts

	run env PATH="$WORK_DIR/bin:/usr/bin:/bin" HOOK_INPUT_JSON="{\"session_id\":\"s_bun_isolate\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	assert_js_args bun.args bun "test --isolate tests/foo.test.ts"
}

@test "test-runner: TEST_RUNNER_FULL runs Bun with --isolate" {
	mkdir -p bin
	touch bun.lock
	cat >bin/bun <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >"$PWD/bun.args"
SH
	chmod +x bin/bun

	run env PATH="$WORK_DIR/bin:/usr/bin:/bin" TEST_RUNNER_FULL=1 HOOK_INPUT_JSON="{\"session_id\":\"s_full_bun\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	assert_js_args bun.args bun "test --isolate"
}

@test "test-runner: default disables package and Makefile fallback" {
	mkdir -p bin src
	cat >package.json <<'JSON'
{"scripts":{"test":"echo test"}}
JSON
	touch package-lock.json src/foo.ts
	cat >bin/npm <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >"$PWD/npm.args"
SH
	chmod +x bin/npm
	write_state s_no_project src/foo.ts

	run env PATH="$WORK_DIR/bin:/usr/bin:/bin" HOOK_INPUT_JSON="{\"session_id\":\"s_no_project\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ ! -f npm.args ]
	[[ "$output" == *"unsupported: no targeted tests ran"* ]]
	[[ "$output" != *"tests passed"* ]]
}

@test "test-runner: npm test script is fallback after focused runners miss" {
	mkdir -p bin src
	cat >package.json <<'JSON'
{"scripts":{"test":"echo test"}}
JSON
	touch package-lock.json src/foo.ts
	cat >bin/npm <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >"$PWD/npm.args"
SH
	chmod +x bin/npm
	write_state s_npm src/foo.ts

	run env HOOK_PROJECT_FALLBACK=1 PATH="$WORK_DIR/bin:/usr/bin:/bin" HOOK_INPUT_JSON="{\"session_id\":\"s_npm\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ "$(cat npm.args)" = "run --silent test" ]
}

@test "test-runner: package script failure reports real exit code" {
	mkdir -p bin src
	cat >package.json <<'JSON'
{"scripts":{"test":"echo test"}}
JSON
	touch package-lock.json src/foo.ts
	cat >bin/npm <<'SH'
#!/usr/bin/env bash
echo npm-failure
exit 7
SH
	chmod +x bin/npm
	write_state s_npm_fail src/foo.ts

	run env HOOK_PROJECT_FALLBACK=1 PATH="$WORK_DIR/bin:/usr/bin:/bin" HOOK_INPUT_JSON="{\"session_id\":\"s_npm_fail\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[[ "$output" == *"npm-failure"* ]]
	[[ "$output" == *"npm test failed with exit 7"* ]]
}

@test "test-runner: package script detection uses node when the Python package lookup fails" {
	mkdir -p bin src
	cat >package.json <<'JSON'
{"scripts":{"test":"echo test"}}
JSON
	touch package-lock.json src/foo.ts
	real_python=$(command -v python3)
	cat >bin/python3 <<SH
#!/usr/bin/env bash
[[ "\$*" == *'Path("package.json")'* ]] && exit 1
exec "$real_python" "\$@"
SH
	cat >bin/node <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >"$PWD/node.args"
exit 0
SH
	cat >bin/npm <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >"$PWD/npm.args"
SH
	chmod +x bin/python3 bin/node bin/npm
	write_state s_node_package src/foo.ts

	run env HOOK_PROJECT_FALLBACK=1 PATH="$WORK_DIR/bin:/usr/bin:/bin" HOOK_INPUT_JSON="{\"session_id\":\"s_node_package\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ -f node.args ]
	[ "$(cat npm.args)" = "run --silent test" ]
}

@test "test-runner: conftest.py is not passed to pytest as a target" {
	mkdir -p bin tests
	cat >pyproject.toml <<'TOML'
[project]
name = "demo"
version = "0.0.0"
TOML
	touch tests/conftest.py
	cat >bin/uv <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >"$PWD/uv.args"
SH
	chmod +x bin/uv
	write_state s_conftest tests/conftest.py

	run env PATH="$WORK_DIR/bin:$PATH" HOOK_INPUT_JSON="{\"session_id\":\"s_conftest\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ ! -f uv.args ]
}

@test "test-runner: pytest exit 5 (no tests collected) is not a failure" {
	mkdir -p bin tests
	cat >pyproject.toml <<'TOML'
[project]
name = "demo"
version = "0.0.0"

[project.optional-dependencies]
test = ["pytest"]
TOML
	touch tests/test_empty.py
	cat >bin/uv <<'SH'
#!/usr/bin/env bash
case "$*" in
*" pytest "*) echo "no tests ran in 0.01s"; exit 5 ;;
*) exit 0 ;;
esac
SH
	chmod +x bin/uv
	write_state s_exit5 tests/test_empty.py

	run env PATH="$WORK_DIR/bin:$PATH" HOOK_INPUT_JSON="{\"session_id\":\"s_exit5\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[[ "$output" == *"skipped: no tests completed"* ]]
	[[ "$output" != *"tests passed"* ]]
}

@test "test-runner: a second Stop with no new edits on a dirty tree is a no-op" {
	mkdir -p bin pkg tests
	cat >pyproject.toml <<'TOML'
[project]
name = "demo"
version = "0.0.0"

[project.optional-dependencies]
test = ["pytest"]
TOML
	touch pkg/foo.py tests/test_foo.py
	cat >bin/uv <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >>"$PWD/uv.calls"
SH
	chmod +x bin/uv
	write_state s_noop pkg/foo.py

	run env PATH="$WORK_DIR/bin:$PATH" HOOK_INPUT_JSON="{\"session_id\":\"s_noop\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	local calls_after_first
	calls_after_first="$(wc -l <uv.calls)"

	# The working tree is still dirty (pkg/foo.py, tests/test_foo.py,
	# pyproject.toml are all untracked) but nothing new was edited since the
	# first Stop concluded. Must not fall back to a git diff and re-run the
	# same tests a second time.
	run env PATH="$WORK_DIR/bin:$PATH" HOOK_INPUT_JSON="{\"session_id\":\"s_noop\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ -z "$output" ]
	[ "$(wc -l <uv.calls)" -eq "$calls_after_first" ]
}

@test "test-runner: a later edit after a no-op Stop is still tested" {
	mkdir -p bin pkg tests
	cat >pyproject.toml <<'TOML'
[project]
name = "demo"
version = "0.0.0"

[project.optional-dependencies]
test = ["pytest"]
TOML
	touch pkg/foo.py tests/test_foo.py
	cat >bin/uv <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >>"$PWD/uv.calls"
SH
	chmod +x bin/uv
	write_state s_later pkg/foo.py

	run env PATH="$WORK_DIR/bin:$PATH" HOOK_INPUT_JSON="{\"session_id\":\"s_later\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	local calls_after_first
	calls_after_first="$(wc -l <uv.calls)"

	# Simulate smart-lint recording a fresh edit on the (now-truncated) state
	# file: this must run tests again, not stay a no-op forever.
	write_state s_later pkg/foo.py

	run env PATH="$WORK_DIR/bin:$PATH" HOOK_INPUT_JSON="{\"session_id\":\"s_later\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ "$(wc -l <uv.calls)" -gt "$calls_after_first" ]
}

@test "test-runner: timeout kills a hung test process and reports skipped: timeout" {
	mkdir -p bin pkg
	touch pkg/foo.go
	cat >bin/go <<SH
#!/usr/bin/env bash
sleep 30
touch "$WORK_DIR/should-not-exist"
SH
	chmod +x bin/go
	write_state s_timeout pkg/foo.go

	run env PATH="$WORK_DIR/bin:$PATH" TEST_RUNNER_TIMEOUT_SECS=1 HOOK_INPUT_JSON="{\"session_id\":\"s_timeout\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[[ "$output" == *"skipped: timeout"* ]]
	[[ "$output" != *"Focused tests passed"* ]]

	# The watchdog kill is asynchronous; give a killed process time to exit
	# and confirm it never reached the line after sleep.
	sleep 3
	[ ! -f "$WORK_DIR/should-not-exist" ]
}

@test "test-runner: a real failure inside the timeout budget is reported without blocking" {
	mkdir -p bin pkg tests
	cat >pyproject.toml <<'TOML'
[project]
name = "demo"
version = "0.0.0"

[project.optional-dependencies]
test = ["pytest"]
TOML
	touch pkg/foo.py tests/test_foo.py
	cat >bin/uv <<'SH'
#!/usr/bin/env bash
case "$*" in
*" pytest "*) echo focused-failure; exit 1 ;;
*) exit 0 ;;
esac
SH
	chmod +x bin/uv
	write_state s_fail_budget pkg/foo.py

	run env PATH="$WORK_DIR/bin:$PATH" TEST_RUNNER_TIMEOUT_SECS=30 HOOK_INPUT_JSON="{\"session_id\":\"s_fail_budget\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[[ "$output" == *"focused-failure"* ]]
	[[ "$output" != *"skipped: timeout"* ]]
}

@test "test-runner: Pi stop envelope (event/piEvent) resolves cwd and session id" {
	mkdir -p bin pkg tests
	cat >pyproject.toml <<'TOML'
[project]
name = "demo"
version = "0.0.0"

[project.optional-dependencies]
test = ["pytest"]
TOML
	touch pkg/foo.py tests/test_foo.py
	cat >bin/uv <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >"$PWD/uv.args"
SH
	chmod +x bin/uv
	write_state s_pi pkg/foo.py

	run env PATH="$WORK_DIR/bin:$PATH" HOOK_INPUT_JSON="{\"event\":\"stop\",\"piEvent\":{\"session_id\":\"s_pi\",\"cwd\":\"$WORK_DIR\"}}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ "$(cat uv.args)" = "run --extra test pytest -q --maxfail=1 --tb=short tests/test_foo.py" ]
}

@test "test-runner: cwd falls back to vendorEvent when piEvent lacks it" {
	mkdir -p bin pkg tests
	cat >pyproject.toml <<'TOML'
[project]
name = "demo"
version = "0.0.0"

[project.optional-dependencies]
test = ["pytest"]
TOML
	touch pkg/foo.py tests/test_foo.py
	cat >bin/uv <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >"$PWD/uv.args"
SH
	chmod +x bin/uv
	write_state s_env pkg/foo.py

	run env PATH="$WORK_DIR/bin:$PATH" HOOK_INPUT_JSON="{\"event\":\"stop\",\"piEvent\":{\"session_id\":\"s_env\"},\"vendorEvent\":{\"cwd\":\"$WORK_DIR\"}}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ "$(cat uv.args)" = "run --extra test pytest -q --maxfail=1 --tb=short tests/test_foo.py" ]
}

@test "test-runner: an edit made outside smart-lint tracking is still tested" {
	mkdir -p bin pkg tests
	cat >pyproject.toml <<'TOML'
[project]
name = "demo"
version = "0.0.0"

[project.optional-dependencies]
test = ["pytest"]
TOML
	touch pkg/foo.py tests/test_foo.py
	git add pkg/foo.py tests/test_foo.py pyproject.toml
	git commit -q -m "initial"
	cat >bin/uv <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >>"$PWD/uv.calls"
SH
	chmod +x bin/uv
	write_state s_bash pkg/foo.py

	run env PATH="$WORK_DIR/bin:$PATH" HOOK_INPUT_JSON="{\"session_id\":\"s_bash\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	local calls_after_first
	calls_after_first="$(wc -l <uv.calls)"

	# Simulate an edit made through the Bash tool (sed -i, git apply,
	# codegen) to a file already tracked by git: the file changes but
	# smart-lint's extractor never records it, so the session state file
	# stays empty. The tree fingerprint must still catch this via the
	# tracked diff and fall back to testing it, not trust the empty state
	# file as "nothing pending".
	printf '# edited via bash\n' >>pkg/foo.py

	run env PATH="$WORK_DIR/bin:$PATH" HOOK_INPUT_JSON="{\"session_id\":\"s_bash\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ "$(wc -l <uv.calls)" -gt "$calls_after_first" ]
}

@test "test-runner: a second Stop with truly no changes stays a no-op after the fingerprint fix" {
	mkdir -p bin pkg tests
	cat >pyproject.toml <<'TOML'
[project]
name = "demo"
version = "0.0.0"

[project.optional-dependencies]
test = ["pytest"]
TOML
	touch pkg/foo.py tests/test_foo.py
	cat >bin/uv <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >>"$PWD/uv.calls"
SH
	chmod +x bin/uv
	write_state s_fp pkg/foo.py

	run env PATH="$WORK_DIR/bin:$PATH" HOOK_INPUT_JSON="{\"session_id\":\"s_fp\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	local calls_after_first
	calls_after_first="$(wc -l <uv.calls)"

	run env PATH="$WORK_DIR/bin:$PATH" HOOK_INPUT_JSON="{\"session_id\":\"s_fp\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ -z "$output" ]
	[ "$(wc -l <uv.calls)" -eq "$calls_after_first" ]
}

@test "test-runner: an invalid TEST_RUNNER_TIMEOUT_SECS falls back to the default" {
	mkdir -p bin pkg tests
	cat >pyproject.toml <<'TOML'
[project]
name = "demo"
version = "0.0.0"

[project.optional-dependencies]
test = ["pytest"]
TOML
	touch pkg/foo.py tests/test_foo.py
	cat >bin/uv <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >"$PWD/uv.args"
SH
	chmod +x bin/uv
	write_state s_bad_a pkg/foo.py

	run env PATH="$WORK_DIR/bin:$PATH" TEST_RUNNER_DEBUG=1 TEST_RUNNER_TIMEOUT_SECS=abc HOOK_INPUT_JSON="{\"session_id\":\"s_bad_a\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[[ "$output" == *"TEST_RUNNER_TIMEOUT_SECS=90"* ]]
	[ "$(cat uv.args)" = "run --extra test pytest -q --maxfail=1 --tb=short tests/test_foo.py" ]

	write_state s_bad_b pkg/foo.py
	run env PATH="$WORK_DIR/bin:$PATH" TEST_RUNNER_DEBUG=1 TEST_RUNNER_TIMEOUT_SECS=1.5 HOOK_INPUT_JSON="{\"session_id\":\"s_bad_b\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[[ "$output" == *"TEST_RUNNER_TIMEOUT_SECS=90"* ]]
}

@test "test-runner: TEST_RUNNER_TIMEOUT_SECS is clamped to [1, 110]" {
	mkdir -p bin pkg
	touch pkg/foo.go
	cat >bin/go <<'SH'
#!/usr/bin/env bash
exit 0
SH
	chmod +x bin/go
	write_state s_clamp_low pkg/foo.go

	run env PATH="$WORK_DIR/bin:$PATH" TEST_RUNNER_DEBUG=1 TEST_RUNNER_TIMEOUT_SECS=0 HOOK_INPUT_JSON="{\"session_id\":\"s_clamp_low\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[[ "$output" == *"TEST_RUNNER_TIMEOUT_SECS=1"* ]]

	write_state s_clamp_high pkg/foo.go
	run env PATH="$WORK_DIR/bin:$PATH" TEST_RUNNER_DEBUG=1 TEST_RUNNER_TIMEOUT_SECS=500 HOOK_INPUT_JSON="{\"session_id\":\"s_clamp_high\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[[ "$output" == *"TEST_RUNNER_TIMEOUT_SECS=110"* ]]
}

@test "test-runner: a leading zero in TEST_RUNNER_TIMEOUT_SECS is read as base 10" {
	mkdir -p bin pkg
	touch pkg/foo.go
	cat >bin/go <<'SH'
#!/usr/bin/env bash
exit 0
SH
	chmod +x bin/go
	write_state s_octal_a pkg/foo.go

	# Bash arithmetic reads a leading-zero literal as octal, and "008" isn't
	# even valid octal — without forcing base 10 this would error out
	# instead of clamping, breaking the timeout budget entirely.
	run env PATH="$WORK_DIR/bin:$PATH" TEST_RUNNER_DEBUG=1 TEST_RUNNER_TIMEOUT_SECS=008 HOOK_INPUT_JSON="{\"session_id\":\"s_octal_a\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[[ "$output" == *"TEST_RUNNER_TIMEOUT_SECS=8"* ]]

	write_state s_octal_b pkg/foo.go
	run env PATH="$WORK_DIR/bin:$PATH" TEST_RUNNER_DEBUG=1 TEST_RUNNER_TIMEOUT_SECS=010 HOOK_INPUT_JSON="{\"session_id\":\"s_octal_b\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[[ "$output" == *"TEST_RUNNER_TIMEOUT_SECS=10"* ]]
}

@test "test-runner: pending state survives a timeout so the file is retried" {
	mkdir -p bin pkg
	touch pkg/foo.go
	cat >bin/go <<SH
#!/usr/bin/env bash
sleep 30
SH
	chmod +x bin/go
	write_state s_keep pkg/foo.go

	run env PATH="$WORK_DIR/bin:$PATH" TEST_RUNNER_TIMEOUT_SECS=1 HOOK_INPUT_JSON="{\"session_id\":\"s_keep\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[[ "$output" == *"skipped: timeout"* ]]

	state_path=$(git rev-parse --git-path "cc-thingz/hooks-v2/hook-files-s_keep")
	[ -s "$state_path" ]
	[ "$(cat "$state_path")" = "pkg/foo.go" ]
}

@test "test-runner: Bun indexes roots once and keeps adjacent tests scoped" {
	mkdir -p bin src tests lib other
	touch bun.lock src/foo.ts src/bar.ts lib/foo.ts other/bar.ts
	touch tests/foo.test.ts tests/bar.spec.ts lib/foo.test.ts other/foo.test.ts
	cat >bin/bun <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >"$PWD/bun.args"
SH
	real_find=$(command -v find)
	cat >bin/find <<SH
#!/usr/bin/env bash
printf '%s\n' "\$*" >>"$WORK_DIR/find.args"
exec "$real_find" "\$@"
SH
	chmod +x bin/bun bin/find
	write_state s_bun_index src/foo.ts src/bar.ts lib/foo.ts other/bar.ts
	run env PATH="$WORK_DIR/bin:$PATH" HOOK_INPUT_JSON="{\"session_id\":\"s_bun_index\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	assert_js_args bun.args bun "test --isolate lib/foo.test.ts tests/bar.spec.ts tests/foo.test.ts"
	[ "$(grep -c '^tests ' find.args)" -eq 1 ]
	[ "$(grep -c '^src ' find.args)" -eq 1 ]
}

setup_python_monorepo() {
	mkdir -p .venv/bin tests api/.venv/bin api/.venv/lib api/tests api/src bin
	printf '[project]\nname = "root"\nversion = "0.0.0"\n' >pyproject.toml
	printf '[project]\nname = "api"\nversion = "0.0.0"\n' >api/pyproject.toml
	touch tests/test_widget.py api/tests/test_widget.py api/src/widget.py
	printf 'import reflex_api\n' >api/tests/conftest.py
	touch api/.venv/lib/reflex_api.py
	cat >.venv/bin/pytest <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$PWD|$*" >>"$PWD/pytest.calls"
exit "${ROOT_PYTEST_EXIT:-0}"
SH
	cat >api/.venv/bin/pytest <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$PWD|$*" >>"$PWD/pytest.calls"
PYTHONPATH="$PWD/.venv/lib" python3 -c 'import runpy; runpy.run_path("tests/conftest.py")' || exit 1
exit "${API_PYTEST_EXIT:-0}"
SH
	chmod +x .venv/bin/pytest api/.venv/bin/pytest
}

@test "test-runner: nested Python tests use their owning venv and relative paths" {
	setup_python_monorepo
	write_state s_nested tests/test_widget.py api/tests/test_widget.py
	run env HOOK_INPUT_JSON="{\"session_id\":\"s_nested\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ "$(cat pytest.calls)" = "$WORK_DIR|-q --maxfail=1 --tb=short tests/test_widget.py" ]
	[ "$(cat api/pytest.calls)" = "$WORK_DIR/api|-q --maxfail=1 --tb=short tests/test_widget.py" ]
	[[ "$output" == *"Python tests in api"* ]]
}

@test "test-runner: Python source mapping stays inside its owning project" {
	setup_python_monorepo
	write_state s_nested_source api/src/widget.py
	run env HOOK_INPUT_JSON="{\"session_id\":\"s_nested_source\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ ! -f pytest.calls ]
	[ "$(cat api/pytest.calls)" = "$WORK_DIR/api|-q --maxfail=1 --tb=short tests/test_widget.py" ]
}

@test "test-runner: Python groups continue after failure and preserve pending state" {
	setup_python_monorepo
	for failing_project in root api; do
		printf '# fail %s\n' "$failing_project" >tests/test_widget.py
		write_state s_nested_failure tests/test_widget.py api/tests/test_widget.py
		root_exit=0 api_exit=0
		if [[ "$failing_project" == root ]]; then root_exit=1; else api_exit=1; fi
		run env ROOT_PYTEST_EXIT="$root_exit" API_PYTEST_EXIT="$api_exit" HOOK_INPUT_JSON="{\"session_id\":\"s_nested_failure\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
		[ "$status" -eq 0 ]
		[ -f pytest.calls ]
		[ -f api/pytest.calls ]
		[ -s "$(git rev-parse --git-path cc-thingz/hooks-v2/hook-files-s_nested_failure)" ]
		rm pytest.calls api/pytest.calls
	done
}

@test "test-runner: nested Python exit 5 is skipped without hiding another group failure" {
	setup_python_monorepo
	write_state s_nested_empty tests/test_widget.py api/tests/test_widget.py
	run env API_PYTEST_EXIT=5 ROOT_PYTEST_EXIT=1 HOOK_INPUT_JSON="{\"session_id\":\"s_nested_empty\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[[ "$output" == *"collected no tests"* ]]
	[ -f api/pytest.calls ]
}

@test "test-runner: uv keeps single-project command and output without syncing the venv" {
	mkdir -p bin tests
	printf '[dependency-groups]\ntest = ["pytest"]\n' >pyproject.toml
	touch tests/test_widget.py
	cat >bin/uv <<'SH'
#!/usr/bin/env bash
[[ "${UV_NO_SYNC:-}" == 1 ]] || exit 99
printf '%s\n' "$*" >>"$PWD/uv.calls"
SH
	chmod +x bin/uv
	write_state s_no_sync tests/test_widget.py
	run env PATH="$WORK_DIR/bin:$PATH" HOOK_INPUT_JSON="{\"session_id\":\"s_no_sync\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ "$(tail -n 1 uv.calls)" = "run --group test pytest -q --maxfail=1 --tb=short tests/test_widget.py" ]
	[[ "$output" == *"Running: uv run --group test pytest -q --maxfail=1 --tb=short tests/test_widget.py"* ]]
	[[ "$output" != *"Python tests in"* ]]
}

@test "test-runner: nested Python uv detection uses the nested dependency group without syncing" {
	setup_python_monorepo
	printf '\n[dependency-groups]\ntest = ["pytest"]\n' >>api/pyproject.toml
	cat >bin/uv <<'SH'
#!/usr/bin/env bash
[[ "${UV_NO_SYNC:-}" == 1 && -f tests/conftest.py ]] || exit 99
printf '%s\n' "$*" >>"$PWD/uv.calls"
[[ "$*" == 'run --group test python -c import pytest' ]] && exit 0
[[ "$*" == 'run --group test pytest -q --maxfail=1 --tb=short tests/test_widget.py' ]] || exit 99
exec .venv/bin/pytest "${@:5}"
SH
	chmod +x bin/uv
	write_state s_nested_uv api/tests/test_widget.py
	run env PATH="$WORK_DIR/bin:$PATH" HOOK_INPUT_JSON="{\"session_id\":\"s_nested_uv\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ -f api/uv.calls ]
	[ ! -f pytest.calls ]
	[ "$(tail -n 1 api/uv.calls)" = "run --group test pytest -q --maxfail=1 --tb=short tests/test_widget.py" ]
}

@test "test-runner: nested Go modules run relative packages from each module" {
	mkdir -p bin pkg api/pkg
	touch go.mod api/go.mod pkg/foo.go api/pkg/foo.go
	cat >bin/go <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$PWD|$*" >>"$PWD/go.calls"
[[ "$PWD" != */api ]]
SH
	chmod +x bin/go
	write_state s_nested_go pkg/foo.go api/pkg/foo.go
	run env PATH="$WORK_DIR/bin:$PATH" HOOK_INPUT_JSON="{\"session_id\":\"s_nested_go\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ "$(cat go.calls)" = "$WORK_DIR|test -json -failfast ./pkg" ]
	[ "$(cat api/go.calls)" = "$WORK_DIR/api|test -json -failfast ./pkg" ]
	[[ "$output" == *"Go tests in api"* ]]
}

@test "test-runner: source mapping prunes child projects under test directories" {
	setup_python_monorepo
	mkdir -p pkg tests/child/tests
	touch pkg/widget.py tests/child/pyproject.toml tests/child/tests/test_widget.py
	write_state s_child_tests pkg/widget.py api/tests/test_widget.py
	run env HOOK_INPUT_JSON="{\"session_id\":\"s_child_tests\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ "$(cat pytest.calls)" = "$WORK_DIR|-q --maxfail=1 --tb=short tests/test_widget.py" ]
	[ -f api/pytest.calls ]
}

@test "test-runner: absolute focus paths are normalized before project grouping" {
	setup_python_monorepo
	write_state s_absolute "$WORK_DIR/api/src/widget.py" api/tests/test_widget.py
	run env HOOK_INPUT_JSON="{\"session_id\":\"s_absolute\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ ! -f pytest.calls ]
	[ "$(cat api/pytest.calls)" = "$WORK_DIR/api|-q --maxfail=1 --tb=short tests/test_widget.py" ]
}

@test "test-runner: focus paths cannot select projects above the hook cwd" {
	setup_python_monorepo
	(cd api && write_state s_outside ../tests/test_widget.py "$WORK_DIR/tests/test_widget.py" tests/test_widget.py)
	run env HOOK_INPUT_JSON="{\"session_id\":\"s_outside\",\"cwd\":\"$WORK_DIR/api\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ ! -f pytest.calls ]
	[ "$(cat api/pytest.calls)" = "$WORK_DIR/api|-q --maxfail=1 --tb=short tests/test_widget.py" ]
}

@test "test-runner: all pytest failures are advisory for native and Pi Stop events" {
	setup_python_monorepo
	for runtime in native pi; do
		input="{\"session_id\":\"s_advisory\",\"cwd\":\"$WORK_DIR\"}"
		[[ "$runtime" == native ]] || input="{\"event\":\"stop\",\"piEvent\":$input}"
		for code in 1 2 3 4 126 127; do
			printf '# %s %s\n' "$runtime" "$code" >tests/test_widget.py
			write_state s_advisory tests/test_widget.py api/tests/test_widget.py
			run env ROOT_PYTEST_EXIT="$code" HOOK_INPUT_JSON="$input" bash "$HOOK"
			[ "$status" -eq 0 ]
			[[ "$output" == *"exit $code"* ]]
			[[ "$output" != *"Focused tests passed"* ]]
			[ -s "$(git rev-parse --git-path cc-thingz/hooks-v2/hook-files-s_advisory)" ]
			[ -f api/pytest.calls ]
			if [[ "$runtime" == pi ]]; then [[ "$output" == *'{"decision":"allow"}'* ]]; fi
			rm pytest.calls api/pytest.calls
		done
	done
}

@test "test-runner: failed full-suite override is advisory and retains pending state" {
	mkdir -p pkg
	touch pkg/foo.go
	write_state s_advisory_full pkg/foo.go
	printf 'test:\n\t@echo full-suite-problem; exit 7\n' >Makefile
	run env TEST_RUNNER_FULL=1 HOOK_INPUT_JSON="{\"session_id\":\"s_advisory_full\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[[ "$output" == *"full-suite-problem"* ]]
	[[ "$output" == *"failed with exit"* ]]
	[ -s "$(git rev-parse --git-path cc-thingz/hooks-v2/hook-files-s_advisory_full)" ]
}

@test "test-runner: missing Python environment cannot turn a partial run into a pass" {
	setup_python_monorepo
	rm .venv/bin/pytest
	real_python=$(command -v python3)
	cat >bin/python3 <<SH
#!/usr/bin/env bash
[[ "\$*" == '-c import pytest' ]] && exit 1
exec "$real_python" "\$@"
SH
	chmod +x bin/python3
	write_state s_partial tests/test_widget.py api/tests/test_widget.py
	run env PATH="$WORK_DIR/bin:$PATH" HOOK_INPUT_JSON="{\"session_id\":\"s_partial\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[[ "$output" == *"pytest not found"* ]]
	[[ "$output" != *"Focused tests passed"* ]]
	[ -f api/pytest.calls ]
	[ -s "$(git rev-parse --git-path cc-thingz/hooks-v2/hook-files-s_partial)" ]
}

@test "test-runner: missing mapped tests are reported without clearing pending source edits" {
	setup_python_monorepo
	mkdir -p pkg
	touch pkg/unmapped.py
	write_state s_unmapped pkg/unmapped.py api/tests/test_widget.py
	run env HOOK_INPUT_JSON="{\"session_id\":\"s_unmapped\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[[ "$output" == *"No focused Python tests found"* ]]
	[[ "$output" != *"Focused tests passed"* ]]
	[ -f api/pytest.calls ]
	[ -s "$(git rev-parse --git-path cc-thingz/hooks-v2/hook-files-s_unmapped)" ]
}

@test "test-runner: a hung uv environment probe is bounded and advisory" {
	setup_python_monorepo
	printf '\n[dependency-groups]\ntest = ["pytest"]\n' >>api/pyproject.toml
	cat >bin/uv <<'SH'
#!/usr/bin/env bash
sleep 30
printf 'probe escaped timeout\n' >probe.finished
SH
	chmod +x bin/uv
	write_state s_probe_timeout api/tests/test_widget.py
	start=$SECONDS
	run env PATH="$WORK_DIR/bin:$PATH" TEST_RUNNER_TIMEOUT_SECS=4 HOOK_INPUT_JSON="{\"session_id\":\"s_probe_timeout\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	elapsed=$((SECONDS - start))
	[ "$status" -eq 0 ]
	[ "$elapsed" -lt 12 ]
	[[ "$output" == *"timeout"* ]]
	[ ! -f api/probe.finished ]
	[ ! -f api/pytest.calls ]
	[ -s "$(git rev-parse --git-path cc-thingz/hooks-v2/hook-files-s_probe_timeout)" ]
}

@test "test-runner: a signalled test runner is reported but cannot block" {
	mkdir -p .venv/bin tests
	touch tests/test_signal.py
	printf '#!/usr/bin/env bash\nkill -TERM "$$"\n' >.venv/bin/pytest
	chmod +x .venv/bin/pytest
	write_state s_runner_signal tests/test_signal.py
	run env HOOK_INPUT_JSON="{\"session_id\":\"s_runner_signal\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[[ "$output" == *"exit 143"* ]]
	[[ "$output" != *"Focused tests passed"* ]]
	[ -s "$(git rev-parse --git-path cc-thingz/hooks-v2/hook-files-s_runner_signal)" ]
}

@test "test-runner: unchanged failed attempts do not repeat, but changed untracked code retries" {
	setup_python_monorepo
	write_state s_attempt api/tests/test_widget.py
	input="{\"session_id\":\"s_attempt\",\"cwd\":\"$WORK_DIR\"}"
	run env API_PYTEST_EXIT=1 HOOK_INPUT_JSON="$input" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ "$(wc -l <api/pytest.calls)" -eq 1 ]
	run env API_PYTEST_EXIT=1 HOOK_INPUT_JSON="$input" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ "$(wc -l <api/pytest.calls)" -eq 1 ]
	[ -z "$output" ]
	[ -s "$(git rev-parse --git-path cc-thingz/hooks-v2/hook-files-s_attempt)" ]
	printf '# changed untracked test\n' >>api/tests/test_widget.py
	run env API_PYTEST_EXIT=1 HOOK_INPUT_JSON="$input" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ "$(wc -l <api/pytest.calls)" -eq 2 ]
}

@test "test-runner: Python source maps to test directories nested inside its project" {
	setup_python_monorepo
	mkdir -p api/components/tests
	mv api/tests/test_widget.py api/components/tests/test_widget.py
	write_state s_deep_python api/src/widget.py
	run env HOOK_INPUT_JSON="{\"session_id\":\"s_deep_python\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ "$(cat api/pytest.calls)" = "$WORK_DIR/api|-q --maxfail=1 --tb=short components/tests/test_widget.py" ]
}

@test "test-runner: nested JS projects use local config and workspace config inheritance" {
	mkdir -p node_modules/.bin web/node_modules/.bin web/tests
	printf '{}\n' >package.json
	printf '{}\n' >web/package.json
	touch vitest.config.ts web/vitest.config.ts
	printf 'test("works", () => {})\n' >web/tests/foo.test.ts
	for runner in node_modules/.bin/vitest web/node_modules/.bin/vitest; do
		printf '#!/usr/bin/env bash\nprintf "%%s\\n" "$PWD|$*" >>vitest.calls\n' >"$runner"
		chmod +x "$runner"
	done
	write_state s_js_local web/tests/foo.test.ts
	run env HOOK_INPUT_JSON="{\"session_id\":\"s_js_local\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	assert_js_args web/vitest.calls vitest "$WORK_DIR/web|run tests/foo.test.ts --passWithNoTests"
	[ ! -f vitest.calls ]
	rm web/vitest.config.ts
	write_state s_js_workspace web/tests/foo.test.ts
	run env HOOK_INPUT_JSON="{\"session_id\":\"s_js_workspace\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	assert_js_args vitest.calls vitest "$WORK_DIR|run web/tests/foo.test.ts --passWithNoTests"
}

@test "test-runner: workspace Bun maps source to tests in its nested package" {
	mkdir -p bin web/src web/tests
	printf '{}\n' >package.json
	printf '{}\n' >web/package.json
	touch bun.lock web/src/foo.ts
	printf 'test("works", () => {})\n' >web/tests/foo.test.ts
	printf '#!/usr/bin/env bash\nprintf "%%s\\n" "$*" >bun.calls\n' >bin/bun
	chmod +x bin/bun
	write_state s_bun_workspace web/src/foo.ts
	run env PATH="$WORK_DIR/bin:/usr/bin:/bin" HOOK_INPUT_JSON="{\"session_id\":\"s_bun_workspace\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	assert_js_args bun.calls bun 'test --isolate web/tests/foo.test.ts'
}

@test "test-runner: real pytest covers nested imports, failed assertions, and collection errors" {
	setup_python_monorepo
	integration_python="$(cd "$BATS_TEST_DIRNAME/../.." && pwd -P)/.venv/bin/python"
	[ -x "$integration_python" ]
	cat >.venv/bin/pytest <<'SH'
#!/usr/bin/env bash
exec "$INTEGRATION_PYTHON" -m pytest "$@"
SH
	cat >api/.venv/bin/pytest <<'SH'
#!/usr/bin/env bash
export PYTHONPATH="$PWD/.venv/lib"
exec "$INTEGRATION_PYTHON" -m pytest "$@"
SH
	printf 'def test_root():\n    assert True\n' >tests/test_widget.py
	printf 'import reflex_api\ndef test_nested():\n    assert reflex_api.VALUE == 42\n' >api/tests/test_widget.py
	printf 'VALUE = 42\n' >api/.venv/lib/reflex_api.py
	input="{\"session_id\":\"s_real_pytest\",\"cwd\":\"$WORK_DIR\"}"
	write_state s_real_pytest tests/test_widget.py api/tests/test_widget.py
	run env INTEGRATION_PYTHON="$integration_python" HOOK_INPUT_JSON="$input" bash "$HOOK"
	[ "$status" -eq 0 ]
	[[ "$output" == *"Focused tests passed"* ]]
	printf 'def test_failure():\n    assert False, "actual-assertion-failure"\n' >api/tests/test_widget.py
	write_state s_real_pytest api/tests/test_widget.py
	run env INTEGRATION_PYTHON="$integration_python" HOOK_INPUT_JSON="$input" bash "$HOOK"
	[ "$status" -eq 0 ]
	[[ "$output" == *"actual-assertion-failure"* ]]
	[[ "$output" != *"Focused tests passed"* ]]
	printf 'import absent_fixture_dependency\n' >api/tests/conftest.py
	write_state s_real_pytest api/tests/test_widget.py
	run env INTEGRATION_PYTHON="$integration_python" HOOK_INPUT_JSON="$input" bash "$HOOK"
	[ "$status" -eq 0 ]
	[[ "$output" == *"ModuleNotFoundError"* ]]
	[[ "$output" != *"Focused tests passed"* ]]
	[ -s "$(git rev-parse --git-path cc-thingz/hooks-v2/hook-files-s_real_pytest)" ]
}

@test "test-runner: unavailable temporary storage is advisory and never starts tests" {
	setup_python_monorepo
	printf '#!/usr/bin/env bash\nprintf "attempt\\n" >>mktemp.calls\nexit 1\n' >bin/mktemp
	chmod +x bin/mktemp
	write_state s_no_temp api/tests/test_widget.py
	run env PATH="$WORK_DIR/bin:$PATH" HOOK_INPUT_JSON="{\"session_id\":\"s_no_temp\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[[ "$output" == *"incomplete"* ]]
	[ ! -f api/pytest.calls ]
	[ -s "$(git rev-parse --git-path cc-thingz/hooks-v2/hook-files-s_no_temp)" ]
	run env PATH="$WORK_DIR/bin:$PATH" HOOK_INPUT_JSON="{\"session_id\":\"s_no_temp\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ -z "$output" ]
	[ "$(wc -l <mktemp.calls)" -eq 1 ]
}

@test "test-runner: zero Go test execution is incomplete, not passed" {
	mkdir -p bin pkg
	touch go.mod pkg/one.go
	cat >bin/go <<'SH'
#!/usr/bin/env bash
printf '%s\n' '{"Action":"skip","Package":"demo/pkg"}'
SH
	chmod +x bin/go
	write_state s_zero_go pkg/one.go
	run env PATH="$WORK_DIR/bin:$PATH" HOOK_INPUT_JSON="{\"session_id\":\"s_zero_go\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[[ "$output" != *"Focused tests passed"* ]]
	[[ "$output" == *"no tests executed"* ]]
	[ -s "$(git rev-parse --git-path cc-thingz/hooks-v2/hook-files-s_zero_go)" ]
}

@test "test-runner: zero JS test execution is incomplete, not passed" {
	mkdir -p node_modules/.bin src
	touch vitest.config.ts src/one.ts
	cat >node_modules/.bin/vitest <<'SH'
#!/usr/bin/env bash
for arg in "$@"; do
	case "$arg" in --outputFile=*) printf '%s\n' '{"numPassedTests":0,"numFailedTests":0}' >"${arg#*=}" ;; esac
done
SH
	chmod +x node_modules/.bin/vitest
	write_state s_zero_js src/one.ts
	run env HOOK_INPUT_JSON="{\"session_id\":\"s_zero_js\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[[ "$output" != *"Focused tests passed"* ]]
	[[ "$output" == *"no tests executed"* ]]
	[ -s "$(git rev-parse --git-path cc-thingz/hooks-v2/hook-files-s_zero_js)" ]
}

@test "test-runner: adding an untracked Bun lockfile retries an incomplete attempt" {
	mkdir -p bin src tests
	touch src/one.ts tests/one.test.ts
	printf '#!/usr/bin/env bash\nprintf "%%s\\n" "$*" >bun.calls\n' >bin/bun
	chmod +x bin/bun
	write_state s_new_lock src/one.ts
	input="{\"session_id\":\"s_new_lock\",\"cwd\":\"$WORK_DIR\"}"
	run env PATH="$WORK_DIR/bin:/usr/bin:/bin" HOOK_INPUT_JSON="$input" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ ! -f bun.calls ]
	touch bun.lock
	run env PATH="$WORK_DIR/bin:/usr/bin:/bin" HOOK_INPUT_JSON="$input" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ -f bun.calls ]
}

@test "test-runner: real Go reports distinguish absent, skipped, and executed tests" {
	mkdir -p pkg
	printf 'module hookfixture\n\ngo 1.22\n' >go.mod
	printf 'package pkg\n' >pkg/one.go
	input="{\"session_id\":\"s_real_go\",\"cwd\":\"$WORK_DIR\"}"
	write_state s_real_go pkg/one.go
	run env GOTOOLCHAIN=local GOPROXY=off GOWORK=off HOOK_INPUT_JSON="$input" bash "$HOOK"
	[ "$status" -eq 0 ]
	[[ "$output" == *"no tests executed"* ]]
	[[ "$output" != *"Focused tests passed"* ]]
	printf 'package pkg\nimport "testing"\nfunc TestSkipped(t *testing.T) { t.Skip("intentional") }\n' >pkg/one_test.go
	write_state s_real_go pkg/one.go
	run env GOTOOLCHAIN=local GOPROXY=off GOWORK=off HOOK_INPUT_JSON="$input" bash "$HOOK"
	[ "$status" -eq 0 ]
	[[ "$output" == *"no tests executed"* ]]
	printf 'package pkg\nimport "testing"\nfunc TestWorks(t *testing.T) { if 1 != 1 { t.Fatal("bad") } }\n' >pkg/one_test.go
	write_state s_real_go pkg/one.go
	run env GOTOOLCHAIN=local GOPROXY=off GOWORK=off HOOK_INPUT_JSON="$input" bash "$HOOK"
	[ "$status" -eq 0 ]
	[[ "$output" == *"Focused tests passed"* ]]
	printf 'package pkg\nimport "testing"\nfunc TestFails(t *testing.T) { t.Fatal("actual-go-failure") }\n' >pkg/one_test.go
	write_state s_real_go pkg/one.go
	run env GOTOOLCHAIN=local GOPROXY=off GOWORK=off HOOK_INPUT_JSON="$input" bash "$HOOK"
	[ "$status" -eq 0 ]
	[[ "$output" == *"actual-go-failure"* ]]
	[[ "$output" != *"Focused tests passed"* ]]
}

@test "test-runner: real Bun reports distinguish skipped and executed tests" {
	mkdir -p tests
	touch bun.lock
	printf 'import {test} from "bun:test"; test.skip("skipped", () => {})\n' >tests/one.test.ts
	input="{\"session_id\":\"s_real_bun\",\"cwd\":\"$WORK_DIR\"}"
	write_state s_real_bun tests/one.test.ts
	run env HOOK_INPUT_JSON="$input" bash "$HOOK"
	[ "$status" -eq 0 ]
	[[ "$output" == *"no tests executed"* ]]
	[[ "$output" != *"Focused tests passed"* ]]
	printf 'import {test,expect} from "bun:test"; test("works", () => { expect(1).toBe(1) })\n' >tests/one.test.ts
	write_state s_real_bun tests/one.test.ts
	run env HOOK_INPUT_JSON="$input" bash "$HOOK"
	[ "$status" -eq 0 ]
	[[ "$output" == *"Focused tests passed"* ]]
	printf 'import {test,expect} from "bun:test"; test("actual-bun-failure", () => { expect(1).toBe(2) })\n' >tests/one.test.ts
	write_state s_real_bun tests/one.test.ts
	run env HOOK_INPUT_JSON="$input" bash "$HOOK"
	[ "$status" -eq 0 ]
	[[ "$output" == *"actual-bun-failure"* ]]
	[[ "$output" != *"Focused tests passed"* ]]
}

@test "test-runner: JS report evidence distinguishes valid and invalid successful exits" {
	mkdir -p node_modules/.bin src
	touch src/one.ts
	input="{\"session_id\":\"s_json_evidence\",\"cwd\":\"$WORK_DIR\"}"
	for kind in vitest jest; do
		touch "$kind.config.js"
		cat >"node_modules/.bin/$kind" <<'SH'
#!/usr/bin/env bash
for arg in "$@"; do
	case "$arg" in --outputFile=*) printf '%s\n' "$TEST_RUNNER_REPORT" >"${arg#*=}" ;; esac
done
SH
		chmod +x "node_modules/.bin/$kind"
		for outcome in passed malformed inconsistent; do
			printf '// %s %s\n' "$kind" "$outcome" >src/one.ts
			case "$outcome" in
			passed) report='{"numPassedTests":1,"numFailedTests":0}' ;;
			malformed) report='invalid json' ;;
			inconsistent) report='{"numPassedTests":0,"numFailedTests":1}' ;;
			esac
			write_state s_json_evidence src/one.ts
			run env TEST_RUNNER_REPORT="$report" HOOK_INPUT_JSON="$input" bash "$HOOK"
			[ "$status" -eq 0 ]
			if [[ "$outcome" == passed ]]; then
				[[ "$output" == *"Focused tests passed"* ]]
			else
				[[ "$output" != *"Focused tests passed"* ]]
				[ -s "$(git rev-parse --git-path cc-thingz/hooks-v2/hook-files-s_json_evidence)" ]
			fi
		done
		rm "$kind.config.js"
	done
}

@test "test-runner: invalid input or a broken metadata runtime never runs unrelated tests" {
	mkdir -p bin pkg
	touch go.mod pkg/one.go
	printf '#!/usr/bin/env bash\ntouch wrong-project-test.used\n' >bin/go
	chmod +x bin/go
	write_state s_bad_metadata pkg/one.go
	run env PATH="$WORK_DIR/bin:$PATH" HOOK_INPUT_JSON='{' bash "$HOOK"
	[ "$status" -eq 0 ]
	[ ! -f wrong-project-test.used ]
	[[ "$output" == *"metadata"* ]]
	printf '#!/usr/bin/env bash\nexit 1\n' >bin/python3
	chmod +x bin/python3
	run env PATH="$WORK_DIR/bin:$PATH" HOOK_INPUT_JSON="{\"cwd\":\"$WORK_DIR\",\"session_id\":\"s_bad_metadata\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ ! -f wrong-project-test.used ]
	[[ "$output" == *"metadata"* ]]
	[ -s "$(git rev-parse --git-path cc-thingz/hooks-v2/hook-files-s_bad_metadata)" ]
}

@test "test-runner: explicit skips retain unverified files for a later enabled run" {
	setup_python_monorepo
	input="{\"session_id\":\"s_explicit_skip\",\"cwd\":\"$WORK_DIR\"}"
	write_state s_explicit_skip api/tests/test_widget.py
	run env SKIP_TESTS=1 HOOK_INPUT_JSON="$input" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ ! -f api/pytest.calls ]
	[ -s "$(git rev-parse --git-path cc-thingz/hooks-v2/hook-files-s_explicit_skip)" ]
	run env HOOK_INPUT_JSON="$input" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ -f api/pytest.calls ]
}

@test "test-runner: increasing the time budget retries a timed-out attempt" {
	mkdir -p bin pkg
	touch go.mod pkg/one.go
	cat >bin/go <<'SH'
#!/usr/bin/env bash
sleep 2
printf '%s\n' '{"Action":"pass","Package":"demo/pkg","Test":"TestWorks"}' '{"Action":"pass","Package":"demo/pkg"}'
SH
	chmod +x bin/go
	write_state s_retry_budget pkg/one.go
	input="{\"session_id\":\"s_retry_budget\",\"cwd\":\"$WORK_DIR\"}"
	run env PATH="$WORK_DIR/bin:$PATH" TEST_RUNNER_TIMEOUT_SECS=1 HOOK_INPUT_JSON="$input" bash "$HOOK"
	[ "$status" -eq 0 ]
	[[ "$output" == *"timeout"* ]]
	run env PATH="$WORK_DIR/bin:$PATH" TEST_RUNNER_TIMEOUT_SECS=15 HOOK_INPUT_JSON="$input" bash "$HOOK"
	[ "$status" -eq 0 ]
	[[ "$output" == *"Focused tests passed"* ]]
}

@test "test-runner: diff fallback is relative to a nested hook cwd" {
	setup_python_monorepo
	git add pyproject.toml api tests .venv
	git commit -q -m 'fixture baseline'
	printf '# changed\n' >>api/tests/test_widget.py
	run env HOOK_INPUT_JSON="{\"session_id\":\"s_nested_diff\",\"cwd\":\"$WORK_DIR/api\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ -f api/pytest.calls ]
	[ ! -f pytest.calls ]
}

@test "test-runner: the same session cannot reuse pending files from a different cwd" {
	setup_python_monorepo
	mkdir -p admin/tests admin/.venv/bin
	printf '[project]\nname = "admin"\nversion = "0.0.0"\n' >admin/pyproject.toml
	touch admin/tests/test_widget.py
	printf '#!/usr/bin/env bash\ntouch pytest.calls\n' >admin/.venv/bin/pytest
	chmod +x admin/.venv/bin/pytest
	git add pyproject.toml api admin tests .venv
	git commit -q -m 'fixture baseline'
	printf '# changed in api\n' >>api/tests/test_widget.py
	run env SKIP_LINT=1 bash "$BATS_TEST_DIRNAME/../../src/hooks/smart-lint/hook.sh" <<JSON
{"cwd":"$WORK_DIR/api","session_id":"same_session","tool_input":{"file_path":"tests/test_widget.py"}}
JSON
	[ "$status" -eq 0 ]
	run env HOOK_INPUT_JSON="{\"session_id\":\"same_session\",\"cwd\":\"$WORK_DIR/admin\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ ! -f admin/pytest.calls ]
	[ -s "$(git rev-parse --git-path cc-thingz/hooks-v2/api/hook-files-same_session)" ]
}

@test "test-runner: a uv workspace member uses its prepared shared environment" {
	mkdir -p api/tests
	printf '[project]\nname = "workspace"\nversion = "0.0.0"\nrequires-python = ">=3.12"\n[tool.uv.workspace]\nmembers = ["api"]\n[dependency-groups]\ndev = ["pytest"]\n' >pyproject.toml
	printf '[project]\nname = "api"\nversion = "0.0.0"\nrequires-python = ">=3.12"\n' >api/pyproject.toml
	prepared_env="$(cd "$BATS_TEST_DIRNAME/../.." && pwd -P)/.venv"
	ln -s "$prepared_env" .venv
	printf 'from pathlib import Path\ndef test_workspace():\n    assert Path.cwd().name == "api"\n' >api/tests/test_workspace.py
	write_state s_uv_workspace api/tests/test_workspace.py
	run env UV_PYTHON_DOWNLOADS=never HOOK_INPUT_JSON="{\"session_id\":\"s_uv_workspace\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[[ "$output" == *"Running: uv run pytest -q --maxfail=1 --tb=short tests/test_workspace.py"* ]]
	[[ "$output" == *"Focused tests passed"* ]]
	[ ! -f uv.lock ]
	[ ! -d api/.venv ]
}
