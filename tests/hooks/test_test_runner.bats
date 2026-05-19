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
	[ "$(cat uv.args)" = "run pytest -q --maxfail=1 --tb=short tests/test_foo.py" ]
}

@test "test-runner: exits 2 on focused test failure" {
	mkdir -p bin pkg tests
	cat >pyproject.toml <<'TOML'
[project]
name = "demo"
version = "0.0.0"
TOML
	touch pkg/foo.py tests/test_foo.py
	cat >bin/uv <<'SH'
#!/usr/bin/env bash
echo focused-failure
exit 1
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

@test "test-runner: Vitest uses related for source files" {
	mkdir -p node_modules/.bin src
	touch vitest.config.ts src/foo.ts
	cat >node_modules/.bin/vitest <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >"$PWD/vitest.args"
SH
	chmod +x node_modules/.bin/vitest
	write_state s_vitest src/foo.ts

	run env HOOK_INPUT_JSON="{\"session_id\":\"s_vitest\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ "$(cat vitest.args)" = "related src/foo.ts --run" ]
}

@test "test-runner: Jest uses findRelatedTests for source files" {
	mkdir -p node_modules/.bin src
	touch jest.config.js src/foo.ts
	cat >node_modules/.bin/jest <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >"$PWD/jest.args"
SH
	chmod +x node_modules/.bin/jest
	write_state s_jest src/foo.ts

	run env HOOK_INPUT_JSON="{\"session_id\":\"s_jest\",\"cwd\":\"$WORK_DIR\"}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ "$(cat jest.args)" = "--findRelatedTests src/foo.ts" ]
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
