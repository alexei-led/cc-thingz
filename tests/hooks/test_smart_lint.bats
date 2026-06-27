#!/usr/bin/env bats

HOOK="$BATS_TEST_DIRNAME/../../src/hooks/smart-lint/hook.sh"

setup() {
	WORK_DIR="${BATS_TEST_TMPDIR:-$(mktemp -d)}"
	mkdir -p "$WORK_DIR"
}

teardown() {
	rm -rf "$WORK_DIR"
}

@test "smart-lint: SKIP_LINT=1 skips all linting and exits 0" {
	run env SKIP_LINT=1 bash "$HOOK"
	[ "$status" -eq 0 ]
}

@test "smart-lint: .nolint file in project root skips linting and exits 0" {
	touch "$WORK_DIR/.nolint"
	run bash -c "cd '$WORK_DIR' && bash '$HOOK'"
	[ "$status" -eq 0 ]
}

@test "smart-lint: lints only the hook input file" {
	cd "$WORK_DIR" || exit
	git init -q
	git config user.email test@example.com
	git config user.name Test
	mkdir -p bin pkg
	touch pyproject.toml pkg/one.py pkg/two.py
	cat >bin/ruff <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >>"$PWD/ruff.args"
SH
	cat >bin/pyright <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >>"$PWD/pyright.args"
SH
	chmod +x bin/ruff bin/pyright

	run env PATH="$WORK_DIR/bin:$PATH" HOOK_INPUT_JSON="{\"session_id\":\"s1\",\"cwd\":\"$WORK_DIR\",\"tool_input\":{\"file_path\":\"pkg/one.py\"}}" bash "$HOOK"
	[ "$status" -eq 0 ]
	grep -q 'pkg/one.py' ruff.args
	run grep -q 'pkg/two.py' ruff.args
	[ "$status" -ne 0 ]
	run grep -q 'format --check' ruff.args
	[ "$status" -ne 0 ]
	grep -q 'pkg/one.py' pyright.args
	grep -q -- '--outputjson' pyright.args
	run grep -q 'pkg/two.py' pyright.args
	[ "$status" -ne 0 ]
	state_path=$(git rev-parse --git-path cc-thingz/hook-files-s1)
	[ "$(cat "$state_path")" = "pkg/one.py" ]
}

@test "smart-lint: pyright JSON output is compact and filters missing imports" {
	cd "$WORK_DIR" || exit
	git init -q
	git config user.email test@example.com
	git config user.name Test
	mkdir -p bin pkg
	touch pyproject.toml pkg/one.py
	cat >bin/ruff <<'SH'
#!/usr/bin/env bash
exit 0
SH
	cat >bin/pyright <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >"$PWD/pyright.args"
cat <<'JSON'
{"generalDiagnostics":[{"file":"pkg/one.py","severity":"error","message":"Import could not be resolved","rule":"reportMissingImports","range":{"start":{"line":0,"character":0}}},{"file":"pkg/one.py","severity":"error","message":"Bad type","rule":"reportGeneralTypeIssues","range":{"start":{"line":1,"character":4}}}]}
JSON
exit 1
SH
	chmod +x bin/ruff bin/pyright

	run env PATH="$WORK_DIR/bin:$PATH" HOOK_INPUT_JSON="{\"session_id\":\"s_pyright\",\"cwd\":\"$WORK_DIR\",\"tool_input\":{\"file_path\":\"pkg/one.py\"}}" bash "$HOOK"
	[ "$status" -eq 2 ]
	grep -q -- '--outputjson' pyright.args
	[[ "$output" == *"pkg/one.py:2:5: error [reportGeneralTypeIssues]: Bad type"* ]]
	[[ "$output" != *"reportMissingImports"* ]]
}

@test "smart-lint: uses local JS tools and never npx or bunx by default" {
	cd "$WORK_DIR" || exit
	git init -q
	git config user.email test@example.com
	git config user.name Test
	mkdir -p bin node_modules/.bin src
	touch package.json src/app.ts
	cat >node_modules/.bin/prettier <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >"$PWD/prettier.args"
SH
	cat >node_modules/.bin/eslint <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >"$PWD/eslint.args"
SH
	cat >bin/npx <<'SH'
#!/usr/bin/env bash
exit 99
SH
	cat >bin/bunx <<'SH'
#!/usr/bin/env bash
exit 99
SH
	chmod +x node_modules/.bin/prettier node_modules/.bin/eslint bin/npx bin/bunx

	run env PATH="$WORK_DIR/bin:$PATH" HOOK_INPUT_JSON="{\"session_id\":\"s_js\",\"cwd\":\"$WORK_DIR\",\"tool_input\":{\"file_path\":\"src/app.ts\"}}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ "$(cat prettier.args)" = "--write src/app.ts" ]
	[ "$(cat eslint.args)" = "--fix src/app.ts" ]
}

@test "smart-lint: Rust uses rustfmt and Cargo clippy on nearest manifest" {
	cd "$WORK_DIR" || exit
	git init -q
	git config user.email test@example.com
	git config user.name Test
	mkdir -p bin crates/app/src
	cat >crates/app/Cargo.toml <<'TOML'
[package]
name = "app"
version = "0.1.0"
edition = "2024"
TOML
	touch crates/app/src/lib.rs
	cat >bin/rustfmt <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >"$PWD/rustfmt.args"
SH
	cat >bin/cargo <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >"$PWD/cargo.args"
SH
	chmod +x bin/rustfmt bin/cargo

	run env PATH="$WORK_DIR/bin:$PATH" HOOK_INPUT_JSON="{\"session_id\":\"s_rust\",\"cwd\":\"$WORK_DIR\",\"tool_input\":{\"file_path\":\"crates/app/src/lib.rs\"}}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ "$(cat rustfmt.args)" = "--edition 2024 crates/app/src/lib.rs" ]
	[ "$(cat cargo.args)" = "clippy --manifest-path crates/app/Cargo.toml --fix --allow-dirty --allow-staged --all-targets -- -D warnings" ]
}

@test "smart-lint: Rust falls back to cargo check when clippy is unavailable" {
	cd "$WORK_DIR" || exit
	git init -q
	git config user.email test@example.com
	git config user.name Test
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
printf '%s\n' "$*" >>"$PWD/cargo.args"
if [ "$1" = "clippy" ]; then
	echo "error: no such command: \`clippy\`" >&2
	exit 101
fi
SH
	chmod +x bin/cargo

	run env PATH="$WORK_DIR/bin:/usr/bin:/bin" HOOK_INPUT_JSON="{\"session_id\":\"s_rust_check\",\"cwd\":\"$WORK_DIR\",\"tool_input\":{\"file_path\":\"src/lib.rs\"}}" bash "$HOOK"
	[ "$status" -eq 0 ]
	grep -q 'clippy --manifest-path Cargo.toml' cargo.args
	grep -q 'check --manifest-path Cargo.toml --all-targets' cargo.args
}

@test "smart-lint: Cargo manifest edits still run Rust lint" {
	cd "$WORK_DIR" || exit
	git init -q
	git config user.email test@example.com
	git config user.name Test
	mkdir -p bin
	cat >Cargo.toml <<'TOML'
[package]
name = "app"
version = "0.1.0"
edition = "2021"
TOML
	cat >bin/cargo <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >"$PWD/cargo.args"
SH
	chmod +x bin/cargo

	run env PATH="$WORK_DIR/bin:/usr/bin:/bin" HOOK_INPUT_JSON="{\"session_id\":\"s_rust_manifest\",\"cwd\":\"$WORK_DIR\",\"tool_input\":{\"file_path\":\"Cargo.toml\"}}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ "$(cat cargo.args)" = "clippy --manifest-path Cargo.toml --fix --allow-dirty --allow-staged --all-targets -- -D warnings" ]
}

@test "smart-lint: C# source edits use dotnet format include on nearest project" {
	cd "$WORK_DIR" || exit
	git init -q
	git config user.email test@example.com
	git config user.name Test
	mkdir -p bin src/App/Controllers
	touch src/App/App.csproj src/App/Controllers/HomeController.cs
	cat >bin/dotnet <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >"$PWD/dotnet.args"
SH
	chmod +x bin/dotnet

	run env PATH="$WORK_DIR/bin:/usr/bin:/bin" HOOK_INPUT_JSON="{\"session_id\":\"s_cs\",\"cwd\":\"$WORK_DIR\",\"tool_input\":{\"file_path\":\"src/App/Controllers/HomeController.cs\"}}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ "$(cat src/App/dotnet.args)" = "format App.csproj --include Controllers/HomeController.cs" ]
}

@test "smart-lint: C# project edits lint the project target" {
	cd "$WORK_DIR" || exit
	git init -q
	git config user.email test@example.com
	git config user.name Test
	mkdir -p bin src/App
	touch src/App/App.csproj
	cat >bin/dotnet <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >"$PWD/dotnet.args"
SH
	chmod +x bin/dotnet

	run env PATH="$WORK_DIR/bin:/usr/bin:/bin" HOOK_INPUT_JSON="{\"session_id\":\"s_csproj\",\"cwd\":\"$WORK_DIR\",\"tool_input\":{\"file_path\":\"src/App/App.csproj\"}}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ "$(cat src/App/dotnet.args)" = "format App.csproj" ]
}

@test "smart-lint: C# props edits prefer the containing solution" {
	cd "$WORK_DIR" || exit
	git init -q
	git config user.email test@example.com
	git config user.name Test
	mkdir -p bin src/App
	touch App.sln Directory.Build.props src/App/App.csproj
	cat >bin/dotnet <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >"$PWD/dotnet.args"
SH
	chmod +x bin/dotnet

	run env PATH="$WORK_DIR/bin:/usr/bin:/bin" HOOK_INPUT_JSON="{\"session_id\":\"s_props\",\"cwd\":\"$WORK_DIR\",\"tool_input\":{\"file_path\":\"Directory.Build.props\"}}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ "$(cat dotnet.args)" = "format App.sln" ]
}

@test "smart-lint: HOOK_PROJECT_FALLBACK=0 disables project fallback" {
	cd "$WORK_DIR" || exit
	git init -q
	git config user.email test@example.com
	git config user.name Test
	mkdir -p bin src
	cat >package.json <<'JSON'
{"scripts":{"lint":"echo lint"}}
JSON
	touch yarn.lock src/app.ts
	cat >bin/yarn <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >"$PWD/yarn.args"
SH
	chmod +x bin/yarn

	run env PATH="$WORK_DIR/bin:/usr/bin:/bin" HOOK_PROJECT_FALLBACK=0 HOOK_INPUT_JSON="{\"session_id\":\"s_no_project\",\"cwd\":\"$WORK_DIR\",\"tool_input\":{\"file_path\":\"src/app.ts\"}}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ ! -f yarn.args ]
}

@test "smart-lint: package lint fallback still runs after focused formatter" {
	cd "$WORK_DIR" || exit
	git init -q
	git config user.email test@example.com
	git config user.name Test
	mkdir -p bin node_modules/.bin src
	cat >package.json <<'JSON'
{"scripts":{"lint":"echo lint"}}
JSON
	touch yarn.lock src/app.ts
	cat >node_modules/.bin/prettier <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >"$PWD/prettier.args"
SH
	cat >bin/yarn <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >"$PWD/yarn.args"
SH
	chmod +x node_modules/.bin/prettier bin/yarn

	run env PATH="$WORK_DIR/bin:/usr/bin:/bin" HOOK_INPUT_JSON="{\"session_id\":\"s_format_then_lint\",\"cwd\":\"$WORK_DIR\",\"tool_input\":{\"file_path\":\"src/app.ts\"}}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ "$(cat prettier.args)" = "--write src/app.ts" ]
	[ "$(cat yarn.args)" = "run lint" ]
}

@test "smart-lint: package lint script is last fallback when focused JS tools are absent" {
	cd "$WORK_DIR" || exit
	git init -q
	git config user.email test@example.com
	git config user.name Test
	mkdir -p bin src
	cat >package.json <<'JSON'
{"scripts":{"lint":"echo lint"}}
JSON
	touch yarn.lock src/app.ts
	cat >bin/yarn <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >"$PWD/yarn.args"
SH
	chmod +x bin/yarn

	run env PATH="$WORK_DIR/bin:/usr/bin:/bin" HOOK_INPUT_JSON="{\"session_id\":\"s_pkg\",\"cwd\":\"$WORK_DIR\",\"tool_input\":{\"file_path\":\"src/app.ts\"}}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ "$(cat yarn.args)" = "run lint" ]
}
