#!/usr/bin/env bats
# shellcheck disable=SC2030,SC2031  # each @test runs in its own subshell; per-test HOME exports are intentionally local

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

	run env -u HOOK_INPUT_JSON PATH="$WORK_DIR/bin:$PATH" bash "$HOOK" <<<"{\"session_id\":\"s1\",\"cwd\":\"$WORK_DIR\",\"tool_input\":{\"file_path\":\"pkg/one.py\"}}"
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

@test "smart-lint: edits outside the project root are skipped, even with unrelated lint errors in the project" {
	cd "$WORK_DIR" || exit
	git init -q
	git config user.email test@example.com
	git config user.name Test
	mkdir -p bin pkg
	touch pyproject.toml
	printf 'x=1\n' >pkg/bad.py
	cat >bin/ruff <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >>"$PWD/ruff.args"
echo "pkg/bad.py:1:1: E225 missing whitespace around operator" >&2
exit 1
SH
	chmod +x bin/ruff

	# Deliberately outside $WORK_DIR (not a subdirectory of it), unlike the
	# nested BATS_TEST_TMPDIR the project itself lives under.
	scratch_dir=$(mktemp -d)

	touch "$scratch_dir/scratch.py"

	run env -u HOOK_INPUT_JSON PATH="$WORK_DIR/bin:$PATH" bash "$HOOK" <<<"{\"session_id\":\"s_outside\",\"cwd\":\"$WORK_DIR\",\"tool_input\":{\"file_path\":\"$scratch_dir/scratch.py\"}}"
	rm -rf "$scratch_dir"
	[ "$status" -eq 0 ]
	[ ! -f ruff.args ]
}

@test "smart-lint: a /tmp scratch edit is skipped (symlinked to /private/tmp on macOS), even with a failing linter" {
	cd "$WORK_DIR" || exit
	git init -q
	git config user.email test@example.com
	git config user.name Test
	touch pyproject.toml
	mkdir -p bin
	cat >bin/ruff <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >>"$PWD/ruff.args"
echo "should never run" >&2
exit 1
SH
	chmod +x bin/ruff

	scratch_dir=$(mktemp -d /tmp/smart-lint-outside.XXXXXX)
	touch "$scratch_dir/scratch.py"

	run env -u HOOK_INPUT_JSON PATH="$WORK_DIR/bin:$PATH" bash "$HOOK" <<<"{\"session_id\":\"s_symlink\",\"cwd\":\"$WORK_DIR\",\"tool_input\":{\"file_path\":\"$scratch_dir/scratch.py\"}}"
	rm -rf "$scratch_dir"
	[ "$status" -eq 0 ]
	[ ! -f ruff.args ]
}

@test "smart-lint: cwd and file_path spelled through different symlink paths to the same real project dir still lints" {
	# cwd given via the /tmp spelling, file_path given via its resolved
	# /private/tmp spelling (or vice versa on a non-macOS box where /tmp
	# isn't a symlink -- skip there since there is nothing to resolve).
	real_tmp=$(cd /tmp && pwd -P)
	[ "$real_tmp" != "/tmp" ] || skip "no /tmp -> $real_tmp symlink on this host"

	project_dir=$(mktemp -d /tmp/smart-lint-proj.XXXXXX)
	cd "$project_dir" || exit
	git init -q
	git config user.email test@example.com
	git config user.name Test
	mkdir -p bin pkg
	touch pyproject.toml
	printf 'x=1\n' >pkg/bad.py
	cat >bin/ruff <<'SH'
#!/usr/bin/env bash
if [[ "$1" == "format" ]]; then exit 0; fi
echo "pkg/bad.py:1:1: E225 missing whitespace around operator" >&2
exit 1
SH
	chmod +x bin/ruff

	resolved_file="$real_tmp/${project_dir#/tmp/}/pkg/bad.py"
	run env -u HOOK_INPUT_JSON PATH="$project_dir/bin:$PATH" bash "$HOOK" <<<"{\"session_id\":\"s_same_real_dir\",\"cwd\":\"$project_dir\",\"tool_input\":{\"file_path\":\"$resolved_file\"}}"
	rm -rf "$project_dir"
	[ "$status" -eq 2 ]
	[[ "$output" == *"E225"* ]]
}

@test "smart-lint: a slow linter (and its child process) is killed after SMART_LINT_CMD_TIMEOUT_SECONDS, without blocking the edit" {
	cd "$WORK_DIR" || exit
	git init -q
	git config user.email test@example.com
	git config user.name Test
	mkdir -p bin pkg
	touch pyproject.toml pkg/one.py
	# A never-ending formatter with its own child process (a grandchild of
	# the hook's direct child): without process-group cleanup on timeout,
	# this child survives as an orphan.
	cat >bin/ruff <<'SH'
#!/usr/bin/env bash
if [[ "$1" == "format" ]]; then
	child_pid_file="$PWD/child.pid"
	sh -c "echo \$\$ > '$child_pid_file'; sleep 999" &
	wait
	exit 0
fi
exit 0
SH
	chmod +x bin/ruff

	run env -u HOOK_INPUT_JSON SMART_LINT_CMD_TIMEOUT_SECONDS=1 PATH="$WORK_DIR/bin:/usr/bin:/bin" bash "$HOOK" <<<"{\"session_id\":\"s_timeout\",\"cwd\":\"$WORK_DIR\",\"tool_input\":{\"file_path\":\"pkg/one.py\"}}"
	# A working kill is the only way this returns instead of hitting bats'
	# own test timeout. The whole point of this hook is to stop blocking
	# edits that have no real lint problem, and a cold/slow tool timing out
	# under load is exactly that case, so it must not block (status 0).
	[ "$status" -eq 0 ]
	[[ "$output" == *"timed out"* ]]

	child_pid=$(cat child.pid 2>/dev/null)
	[ -n "$child_pid" ]
	for _ in 1 2 3; do
		kill -0 "$child_pid" 2>/dev/null || break
		sleep 1
	done
	run kill -0 "$child_pid"
	[ "$status" -ne 0 ]
}

@test "smart-lint: run_with_timeout returns quickly for a fast command captured via \$(...)" {
	source "$BATS_TEST_DIRNAME/../../src/hooks/smart-lint/smart-lint/lib.sh"
	start=$(date +%s)
	x=$(run_with_timeout 20 true)
	end=$(date +%s)
	[ "$((end - start))" -lt 5 ]
	[ -z "$x" ]
}

@test "smart-lint: SMART_LINT_CMD_TIMEOUT_SECONDS falls back to 30 when non-numeric or zero" {
	for bad in "" "abc" "0" "-5" "15abc"; do
		run env SMART_LINT_CMD_TIMEOUT_SECONDS="$bad" bash -c '
			source "'"$BATS_TEST_DIRNAME"'/../../src/hooks/smart-lint/smart-lint/lib.sh"
			echo "$SMART_LINT_CMD_TIMEOUT_SECONDS"
		'
		[ "$output" = "30" ]
	done
}

@test "smart-lint: a notebook edit outside the project root is skipped" {
	cd "$WORK_DIR" || exit
	git init -q
	git config user.email test@example.com
	git config user.name Test
	touch pyproject.toml

	scratch_dir=$(mktemp -d)
	touch "$scratch_dir/scratch.ipynb"

	run env -u HOOK_INPUT_JSON bash "$HOOK" <<<"{\"session_id\":\"s_notebook\",\"cwd\":\"$WORK_DIR\",\"tool_input\":{\"notebook_path\":\"$scratch_dir/scratch.ipynb\"}}"
	rm -rf "$scratch_dir"
	[ "$status" -eq 0 ]
}

@test "smart-lint: a patch touching only out-of-project files is skipped, but one in-project file is not" {
	cd "$WORK_DIR" || exit
	git init -q
	git config user.email test@example.com
	git config user.name Test
	touch pyproject.toml

	scratch_dir=$(mktemp -d)
	patch=$'diff --git a/'"$scratch_dir"'/x.py b/'"$scratch_dir"'/x.py\n--- a/'"$scratch_dir"'/x.py\n+++ b/'"$scratch_dir"'/x.py\n'
	payload=$(python3 -c 'import json,sys; print(json.dumps({"session_id":"p1","cwd":sys.argv[1],"tool_input":{"patch":sys.argv[2]}}))' "$WORK_DIR" "$patch")
	run env -u HOOK_INPUT_JSON bash "$HOOK" <<<"$payload"
	rm -rf "$scratch_dir"
	[ "$status" -eq 0 ]
	[[ "$output" != *"Style OK"* ]]

	mkdir -p pkg
	patch=$'diff --git a/pkg/one.py b/pkg/one.py\n--- a/pkg/one.py\n+++ b/pkg/one.py\n'
	payload=$(python3 -c 'import json,sys; print(json.dumps({"session_id":"p2","cwd":sys.argv[1],"tool_input":{"patch":sys.argv[2]}}))' "$WORK_DIR" "$patch")
	run env -u HOOK_INPUT_JSON CLAUDE_HOOKS_DEBUG=1 bash "$HOOK" <<<"$payload"
	[[ "$output" != *"outside the project root"* ]]
}

@test "smart-lint: an Agent Bundler envelope payload resolves cwd from vendorEvent, not the inherited process cwd" {
	cd "$WORK_DIR" || exit
	git init -q
	git config user.email test@example.com
	git config user.name Test
	mkdir -p bin pkg
	touch pyproject.toml
	printf 'x=1\n' >pkg/bad.py
	cat >bin/ruff <<'SH'
#!/usr/bin/env bash
if [[ "$1" == "format" ]]; then exit 0; fi
echo "pkg/bad.py:1:1: E225 missing whitespace around operator" >&2
exit 1
SH
	chmod +x bin/ruff

	payload=$(python3 -c '
import json, sys
work_dir = sys.argv[1]
payload = {
    "event": "post-tool",
    "hook": "smart-lint",
    "piEvent": {"toolName": "edit", "input": {"file_path": "pkg/bad.py"}},
    "vendorEvent": {"cwd": work_dir, "session_id": "envelope", "tool_input": {"file_path": "pkg/bad.py"}},
}
print(json.dumps(payload))
' "$WORK_DIR")

	# Run from outside the project entirely so an inherited OS cwd can't
	# paper over a broken vendorEvent.cwd fallback.
	run env -u HOOK_INPUT_JSON PATH="$WORK_DIR/bin:$PATH" bash -c "cd / && bash '$HOOK' <<<'$payload'"
	[ "$status" -eq 2 ]
	[[ "$output" == *"E225"* ]]
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
	touch package.json .prettierrc eslint.config.js src/app.ts
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

@test "smart-lint: adopted Biome combines formatting and linting" {
	cd "$WORK_DIR" || exit
	git init -q
	git config user.email test@example.com
	git config user.name Test
	mkdir -p bin src
	printf '{}\n' >biome.json
	printf '{}\n' >package.json
	touch src/app.ts
	cat >bin/biome <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >"$PWD/biome.args"
SH
	cat >bin/prettier <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >"$PWD/prettier.args"
exit 99
SH
	cat >bin/eslint <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >"$PWD/eslint.args"
exit 99
SH
	chmod +x bin/biome bin/prettier bin/eslint

	run env PATH="$WORK_DIR/bin:$PATH" HOOK_INPUT_JSON="{\"session_id\":\"s_biome\",\"cwd\":\"$WORK_DIR\",\"tool_input\":{\"file_path\":\"src/app.ts\"}}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ "$(cat biome.args)" = "check --write src/app.ts" ]
	[ ! -f prettier.args ]
	[ ! -f eslint.args ]
}

@test "smart-lint: adopted Oxfmt owns formatting while Oxlint lints" {
	cd "$WORK_DIR" || exit
	git init -q
	git config user.email test@example.com
	git config user.name Test
	mkdir -p bin src
	printf '{}\n' >.oxfmtrc.json
	printf '{}\n' >.oxlintrc.json
	touch src/app.ts
	cat >bin/oxfmt <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >"$PWD/oxfmt.args"
SH
	cat >bin/oxlint <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >"$PWD/oxlint.args"
SH
	chmod +x bin/oxfmt bin/oxlint

	run env PATH="$WORK_DIR/bin:$PATH" HOOK_INPUT_JSON="{\"session_id\":\"s_oxfmt\",\"cwd\":\"$WORK_DIR\",\"tool_input\":{\"file_path\":\"src/app.ts\"}}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ "$(cat oxfmt.args)" = "--write src/app.ts" ]
	[ "$(cat oxlint.args)" = "--fix src/app.ts" ]
}

@test "smart-lint: adopted Oxlint owns lint while Biome formats" {
	cd "$WORK_DIR" || exit
	git init -q
	git config user.email test@example.com
	git config user.name Test
	mkdir -p bin src
	printf '{}\n' >biome.json
	printf '{}\n' >.oxlintrc.json
	touch src/app.ts
	cat >bin/biome <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >"$PWD/biome.args"
SH
	cat >bin/oxlint <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >"$PWD/oxlint.args"
SH
	chmod +x bin/biome bin/oxlint

	run env PATH="$WORK_DIR/bin:$PATH" HOOK_INPUT_JSON="{\"session_id\":\"s_oxlint\",\"cwd\":\"$WORK_DIR\",\"tool_input\":{\"file_path\":\"src/app.ts\"}}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ "$(cat biome.args)" = "format --write src/app.ts" ]
	[ "$(cat oxlint.args)" = "--fix src/app.ts" ]
}

@test "smart-lint: available Biome and Oxlint are used without project config" {
	cd "$WORK_DIR" || exit
	git init -q
	git config user.email test@example.com
	git config user.name Test
	mkdir -p bin src
	printf '{}\n' >package.json
	touch src/app.ts
	for tool in biome oxlint; do
		cat >"bin/$tool" <<SH
#!/usr/bin/env bash
printf '%s\\n' "\$*" >"\$PWD/$tool.args"
SH
	done
	cat >bin/prettier <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >"$PWD/prettier.args"
exit 99
SH
	cat >bin/eslint <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >"$PWD/eslint.args"
exit 99
SH
	chmod +x bin/biome bin/oxlint bin/prettier bin/eslint

	run env PATH="$WORK_DIR/bin:$PATH" HOOK_INPUT_JSON="{\"session_id\":\"s_machine\",\"cwd\":\"$WORK_DIR\",\"tool_input\":{\"file_path\":\"src/app.ts\"}}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ "$(cat biome.args)" = "format --write src/app.ts" ]
	[ "$(cat oxlint.args)" = "--fix src/app.ts" ]
	[ ! -f prettier.args ]
	[ ! -f eslint.args ]
}

@test "smart-lint: package-declared Biome enables an installed binary" {
	cd "$WORK_DIR" || exit
	git init -q
	git config user.email test@example.com
	git config user.name Test
	mkdir -p bin src
	cat >package.json <<'JSON'
{"devDependencies":{"@biomejs/biome":"latest"}}
JSON
	touch src/app.ts
	cat >bin/biome <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >"$PWD/biome.args"
SH
	chmod +x bin/biome

	run env PATH="$WORK_DIR/bin:$PATH" HOOK_INPUT_JSON="{\"session_id\":\"s_biome_package\",\"cwd\":\"$WORK_DIR\",\"tool_input\":{\"file_path\":\"src/app.ts\"}}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ "$(cat biome.args)" = "check --write src/app.ts" ]
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

@test "smart-lint: Java files use google-java-format on the edited file" {
	cd "$WORK_DIR" || exit
	git init -q
	git config user.email test@example.com
	git config user.name Test
	mkdir -p bin src/main/java/com/example
	touch build.gradle src/main/java/com/example/App.java
	cat >bin/google-java-format <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >"$PWD/google-java-format.args"
SH
	chmod +x bin/google-java-format

	run env PATH="$WORK_DIR/bin:/usr/bin:/bin" HOOK_INPUT_JSON="{\"session_id\":\"s_java\",\"cwd\":\"$WORK_DIR\",\"tool_input\":{\"file_path\":\"src/main/java/com/example/App.java\"}}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ "$(cat google-java-format.args)" = "-i src/main/java/com/example/App.java" ]
}

@test "smart-lint: Kotlin files use ktlint format and detekt input" {
	cd "$WORK_DIR" || exit
	git init -q
	git config user.email test@example.com
	git config user.name Test
	mkdir -p bin src/main/kotlin/com/example
	touch build.gradle.kts src/main/kotlin/com/example/App.kt
	cat >bin/ktlint <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >"$PWD/ktlint.args"
SH
	cat >bin/detekt <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >"$PWD/detekt.args"
SH
	chmod +x bin/ktlint bin/detekt

	run env PATH="$WORK_DIR/bin:/usr/bin:/bin" HOOK_INPUT_JSON="{\"session_id\":\"s_kotlin\",\"cwd\":\"$WORK_DIR\",\"tool_input\":{\"file_path\":\"src/main/kotlin/com/example/App.kt\"}}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ "$(cat ktlint.args)" = "--format src/main/kotlin/com/example/App.kt" ]
	[ "$(cat detekt.args)" = "--input src/main/kotlin/com/example/App.kt" ]
}

@test "smart-lint: Gradle Kotlin build edits run a fast Gradle sanity task" {
	cd "$WORK_DIR" || exit
	git init -q
	git config user.email test@example.com
	git config user.name Test
	touch build.gradle.kts
	cat >gradlew <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >"$PWD/gradle.args"
SH
	chmod +x gradlew

	run env PATH="/usr/bin:/bin" HOOK_INPUT_JSON="{\"session_id\":\"s_gradle_build\",\"cwd\":\"$WORK_DIR\",\"tool_input\":{\"file_path\":\"build.gradle.kts\"}}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ "$(cat gradle.args)" = "help --quiet" ]
}

@test "smart-lint: default disables project fallback" {
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

	run env PATH="$WORK_DIR/bin:/usr/bin:/bin" HOOK_INPUT_JSON="{\"session_id\":\"s_no_project\",\"cwd\":\"$WORK_DIR\",\"tool_input\":{\"file_path\":\"src/app.ts\"}}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ ! -f yarn.args ]
	[[ "$output" == *"unsupported: no lint checks completed"* ]]
	[[ "$output" != *"Style OK"* ]]
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

	run env HOOK_PROJECT_FALLBACK=1 PATH="$WORK_DIR/bin:/usr/bin:/bin" HOOK_INPUT_JSON="{\"session_id\":\"s_format_then_lint\",\"cwd\":\"$WORK_DIR\",\"tool_input\":{\"file_path\":\"src/app.ts\"}}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ "$(cat prettier.args)" = "--write src/app.ts" ]
	[ "$(cat yarn.args)" = "run lint" ]
}

@test "smart-lint: untrusted project .claude-hooks-config.sh is not sourced" {
	cd "$WORK_DIR" || exit
	export HOME="$WORK_DIR/home"
	mkdir -p "$HOME/.claude"
	cat >.claude-hooks-config.sh <<'SH'
touch marker
SH

	run env SKIP_LINT=1 bash "$HOOK"
	[ "$status" -eq 0 ]
	[ ! -f marker ]
	[[ "$output" == *"ignoring untrusted"* ]]
}

@test "smart-lint: hash-trusted project .claude-hooks-config.sh is sourced" {
	cd "$WORK_DIR" || exit
	export HOME="$WORK_DIR/home"
	mkdir -p "$HOME/.claude"
	cat >.claude-hooks-config.sh <<'SH'
touch marker
SH
	shasum -a 256 .claude-hooks-config.sh | awk '{print $1}' >>"$HOME/.claude/trusted-hooks-config-hashes"

	run env SKIP_LINT=1 bash "$HOOK"
	[ "$status" -eq 0 ]
	[ -f marker ]
}

@test "smart-lint: CLAUDE_HOOKS_TRUST_PROJECT_CONFIG=1 sources untrusted project config" {
	cd "$WORK_DIR" || exit
	export HOME="$WORK_DIR/home"
	mkdir -p "$HOME/.claude"
	cat >.claude-hooks-config.sh <<'SH'
touch marker
SH

	run env SKIP_LINT=1 CLAUDE_HOOKS_TRUST_PROJECT_CONFIG=1 bash "$HOOK"
	[ "$status" -eq 0 ]
	[ -f marker ]
}

@test "smart-lint: stale hash after config edit is no longer trusted" {
	cd "$WORK_DIR" || exit
	export HOME="$WORK_DIR/home"
	mkdir -p "$HOME/.claude"
	cat >.claude-hooks-config.sh <<'SH'
touch marker
SH
	shasum -a 256 .claude-hooks-config.sh | awk '{print $1}' >>"$HOME/.claude/trusted-hooks-config-hashes"
	echo '# modified' >>.claude-hooks-config.sh

	run env SKIP_LINT=1 bash "$HOOK"
	[ "$status" -eq 0 ]
	[ ! -f marker ]
}

@test "smart-lint: user-level .claude-hooks-config.sh still sources unconditionally" {
	cd "$WORK_DIR" || exit
	export HOME="$WORK_DIR/home"
	mkdir -p "$HOME/.claude"
	cat >"$HOME/.claude/.claude-hooks-config.sh" <<'SH'
touch marker
SH

	run env SKIP_LINT=1 bash "$HOOK"
	[ "$status" -eq 0 ]
	[ -f marker ]
	[[ "$output" != *"ignoring untrusted"* ]]
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

	run env HOOK_PROJECT_FALLBACK=1 PATH="$WORK_DIR/bin:/usr/bin:/bin" HOOK_INPUT_JSON="{\"session_id\":\"s_pkg\",\"cwd\":\"$WORK_DIR\",\"tool_input\":{\"file_path\":\"src/app.ts\"}}" bash "$HOOK"
	[ "$status" -eq 0 ]
	[ "$(cat yarn.args)" = "run lint" ]
}
