#!/usr/bin/env bats

HOOK="$BATS_TEST_DIRNAME/../../src/hooks/test-runner/hook.sh"

setup() {
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
	local state_path
	state_path=$(git rev-parse --git-path "cc-thingz/hook-files-$session_id")
	mkdir -p "$(dirname "$state_path")"
	printf '%s\n' "$@" >"$state_path"
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

@test "test-runner: exits 2 on focused test failure" {
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
	[ "$status" -eq 2 ]
	[[ "$output" == *"focused-failure"* ]]
}

@test "test-runner: uses nearest non-root Makefile target as fallback" {
	mkdir -p setup/files
	touch setup/files/foo.py
	cat >setup/Makefile <<'MAKE'
test:
	@echo setup-test > ../make.marker
MAKE
	write_state s2 setup/files/foo.py

	run env HOOK_INPUT_JSON="{\"session_id\":\"s2\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
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

	run env PATH="$WORK_DIR/bin:/usr/bin:/bin" HOOK_INPUT_JSON="{\"session_id\":\"s_make_first\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ "$(cat make.marker)" = "setup-test" ]
	[ ! -f go.args ]
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
	[ "$(cat vitest.args)" = "run --passWithNoTests" ]
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
	[ "$(cat jest.args)" = "--passWithNoTests" ]
}

@test "test-runner: TEST_RUNNER_FULL runs Bats when shell tests exist" {
	mkdir -p bin tests
	cat >tests/test_smoke.bats <<'BATS'
#!/usr/bin/env bats
@test "smoke" { true; }
BATS
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
	[ "$(cat go.args)" = "test -failfast ./pkg" ]
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
	[ "$(cat vitest.args)" = "related src/foo.ts --run --passWithNoTests" ]
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
	[ "$(cat vitest.args)" = "related tests/helper.ts --run --passWithNoTests" ]
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
	[ "$(cat vitest.args)" = "run tests/foo.ts --passWithNoTests" ]
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
	[ "$(cat jest.args)" = "--findRelatedTests src/foo.ts --passWithNoTests" ]
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

@test "test-runner: HOOK_PROJECT_FALLBACK=0 disables package and Makefile fallback" {
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

	run env PATH="$WORK_DIR/bin:/usr/bin:/bin" HOOK_PROJECT_FALLBACK=0 HOOK_INPUT_JSON="{\"session_id\":\"s_no_project\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ ! -f npm.args ]
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

	run env PATH="$WORK_DIR/bin:/usr/bin:/bin" HOOK_INPUT_JSON="{\"session_id\":\"s_npm\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
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

	run env PATH="$WORK_DIR/bin:/usr/bin:/bin" HOOK_INPUT_JSON="{\"session_id\":\"s_npm_fail\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 2 ]
	[[ "$output" == *"npm-failure"* ]]
	[[ "$output" == *"npm test failed with exit 7"* ]]
}

@test "test-runner: package script detection uses node when python3 is unusable" {
	mkdir -p bin src
	cat >package.json <<'JSON'
{"scripts":{"test":"echo test"}}
JSON
	touch package-lock.json src/foo.ts
	cat >bin/python3 <<'SH'
#!/usr/bin/env bash
exit 1
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

	run env PATH="$WORK_DIR/bin:/usr/bin:/bin" HOOK_INPUT_JSON="{\"session_id\":\"s_node_package\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
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
}
