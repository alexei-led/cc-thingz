"""Agent Bundler hook and Pi compatibility-stack integration contracts."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from conftest import REPO_ROOT

PI_PORTABLE_HOOKS = {
    "hook/session-start",
    "hook/file-protector",
    "hook/git-guardrails",
    "hook/release-guard",
    "hook/smart-lint",
    "hook/test-runner",
}
TARGETS = {"claude", "codex", "pi", "copilot", "cursor", "grok"}
GUARD_TARGETS = {
    "claude": {"file-protector", "git-guardrails"},
    "codex": {"file-protector", "git-guardrails"},
    "copilot": {"file-protector", "git-guardrails"},
    "cursor": {"git-guardrails"},
    "grok": {"file-protector", "git-guardrails"},
    "pi": {"file-protector", "git-guardrails"},
}


def _generated_hook_paths(target: str, hook_name: str) -> list[Path]:
    return list((REPO_ROOT / "dist" / target).rglob(hook_name))


def test_agentbundler_renders_pi_portable_and_compatibility_hook_contracts() -> None:
    # dist/ is built once for the whole session in conftest.pytest_sessionstart.
    manifest = json.loads((REPO_ROOT / "dist/pi/hooks/hooks.v1.json").read_text())
    hooks = {entry["identity"]: entry for entry in manifest["hooks"]}

    assert set(hooks) == PI_PORTABLE_HOOKS
    assert hooks["hook/file-protector"]["failurePolicy"] == "closed"
    assert hooks["hook/git-guardrails"]["matcher"]["tools"] == ["command"]
    assert hooks["hook/release-guard"]["failurePolicy"] == "closed"
    assert hooks["hook/release-guard"]["matcher"]["tools"] == ["command"]
    assert hooks["hook/release-guard"]["environment"] == ["HOOK_RELEASE_GUARD"]
    assert hooks["hook/release-guard"]["handler"] == {
        "mode": "exec",
        "program": "bash",
        "arguments": [
            {"packageFile": "hooks/payloads/release-guard/hook.sh"},
            {"packageFile": "hooks/payloads/release-guard/hook.py"},
        ],
    }
    assert (REPO_ROOT / "dist/pi/extensions/agentbundler-hooks.ts").is_file()

    compatibility = json.loads(
        (REPO_ROOT / "dist/pi/extensions/hooks.json").read_text()
    )
    assert compatibility == {"hooks": {}}


def test_agentbundler_renders_target_hook_matrix() -> None:

    for target, expected in GUARD_TARGETS.items():
        for hook_name in ("file-protector", "git-guardrails"):
            assert bool(_generated_hook_paths(target, hook_name)) is (
                hook_name in expected
            )
    for target in TARGETS:
        release_guard_paths = _generated_hook_paths(target, "release-guard")
        assert release_guard_paths
        for release_guard_path in release_guard_paths:
            assert (release_guard_path / "hook.sh").is_file()

    codex_hooks = json.loads(
        (REPO_ROOT / "dist/codex/dev-flow/hooks/hooks.json").read_text()
    )
    assert (
        codex_hooks["hooks"]["PostToolUse"][0]["matcher"]
        == "^apply_patch$|^Edit$|^Write$"
    )
    assert "smart-lint" in codex_hooks["hooks"]["PostToolUse"][0]["hooks"][0]["command"]


def test_generated_pi_runtime_executes_real_git_guard_with_safe_environment(
    tmp_path: Path,
) -> None:
    config = tmp_path / "hook-config.json"
    config.write_text(
        json.dumps({"git-guardrails": {"block_patterns": ["git[[:space:]]+status"]}})
    )
    script = r"""
import { readFileSync } from "node:fs";
import { runProcess } from "./dist/pi/extensions/_agentbundler-hooks/index.ts";
const manifest = JSON.parse(readFileSync("./dist/pi/hooks/hooks.v1.json", "utf8"));
const hook = manifest.hooks.find((entry) => entry.identity === "hook/git-guardrails");
const config = process.env.CLAUDE_HOOK_CONFIG;
delete process.env.CLAUDE_HOOK_CONFIG;
const cases = [
  ["git status", false],
  ["git reset --hard", false],
  ["git status", true],
];
for (const [command, configured] of cases) {
  if (configured && config !== undefined) {
    process.env.CLAUDE_HOOK_CONFIG = config;
  }
  const result = await runProcess(hook.handler, {
    packageRoot: "./dist/pi",
    input: {
      event: "pre-tool",
      hook: hook.identity,
      piEvent: { toolName: "bash", input: { command } },
    },
    // Test-only budget, decoupled from the hook's shipped 10s timeout: this
    // asserts on the deny/allow decision and env sanitization, not latency,
    // so a CPU-starved CI runner shouldn't force-kill an otherwise-correct run.
    timeoutMilliseconds: 60000,
    environment: hook.environment,
  });
  console.log(JSON.stringify({
    command,
    configured,
    exitCode: result.exitCode,
    stdout: result.stdout,
    stderr: result.stderr,
  }));
}
"""
    environment = os.environ.copy()
    environment["CLAUDE_HOOK_CONFIG"] = str(config)
    environment["CC_THINGZ_SECRET_SENTINEL"] = "must-not-reach-hook"
    result = subprocess.run(
        ["bun", "-e", script],
        cwd=REPO_ROOT,
        env=environment,
        capture_output=True,
        check=True,
        text=True,
        # Generous outer bound: a safety net against a true hang, well above
        # the 3 sequential 60s per-case budgets above.
        timeout=200,
    )
    status, reset, configured = [
        json.loads(line) for line in result.stdout.splitlines()
    ]

    assert status == {
        "command": "git status",
        "configured": False,
        "exitCode": 0,
        "stdout": "",
        "stderr": "",
    }
    assert reset["exitCode"] == 0
    assert json.loads(reset["stdout"])["decision"] == "deny"
    assert json.loads(configured["stdout"])["decision"] == "deny"


def test_pi_decision_guards_emit_runtime_protocol() -> None:
    file_protector = subprocess.run(
        ["python3", "src/hooks/file-protector/hook.py"],
        cwd=REPO_ROOT,
        input='{"event":"pre-tool","piEvent":{"input":{"path":"server.key"}}}',
        capture_output=True,
        check=True,
        text=True,
    )
    env_edit = subprocess.run(
        ["python3", "src/hooks/file-protector/hook.py"],
        cwd=REPO_ROOT,
        input='{"event":"pre-tool","piEvent":{"input":{"path":".env"}}}',
        capture_output=True,
        check=True,
        text=True,
    )
    git_guardrails = subprocess.run(
        [
            "bash",
            "src/hooks/git-guardrails/hook.sh",
            "src/hooks/git-guardrails/decide.py",
        ],
        cwd=REPO_ROOT,
        input='{"event":"pre-tool","piEvent":{"input":{"command":"git reset --hard"}}}',
        capture_output=True,
        check=True,
        text=True,
    )

    assert json.loads(file_protector.stdout)["decision"] == "deny"
    assert json.loads(env_edit.stdout)["decision"] == "allow"
    assert json.loads(git_guardrails.stdout)["decision"] == "deny"


def test_generated_pi_release_guard_denies_invalid_notes_with_pi_envelope(
    tmp_path: Path,
) -> None:
    notes = tmp_path / "notes.md"
    notes.write_text("TODO: fill in notes\n")
    command = (
        f"gh release create v6.13.0 --repo alexei-led/cc-thingz --verify-tag "
        f"--title v6.13.0 --notes-file {notes}"
    )
    script = r"""
import { readFileSync } from "node:fs";
import { runProcess } from "./dist/pi/extensions/_agentbundler-hooks/index.ts";
const manifest = JSON.parse(readFileSync("./dist/pi/hooks/hooks.v1.json", "utf8"));
const hook = manifest.hooks.find((entry) => entry.identity === "hook/release-guard");
const result = await runProcess(hook.handler, {
  packageRoot: "./dist/pi",
  input: {
    event: "pre-tool",
    hook: hook.identity,
    piEvent: {
      cwd: process.env.HOME,
      toolName: "bash",
      input: { command: process.env.RELEASE_COMMAND },
    },
  },
  // Test-only budget: see the git-guardrails test above for why this
  // doesn't reuse the hook's shipped 10s timeout.
  timeoutMilliseconds: 60000,
  environment: hook.environment,
});
console.log(JSON.stringify(result));
"""
    result = subprocess.run(
        ["bun", "-e", script],
        cwd=REPO_ROOT,
        env={
            **os.environ,
            "HOME": str(tmp_path),
            "HOOK_RELEASE_GUARD": "1",
            "RELEASE_COMMAND": command,
        },
        capture_output=True,
        text=True,
        check=True,
        # Generous outer bound: see the git-guardrails test above.
        timeout=90,
    )
    outcome = json.loads(result.stdout)
    assert outcome["exitCode"] == 0, outcome["stderr"]
    assert json.loads(outcome["stdout"]) == {
        "decision": "deny",
        "reason": "release-guard: release notes need meaningful user-visible content",
    }


def test_generated_pi_smart_lint_preserves_project_file_and_session(
    tmp_path: Path,
) -> None:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "one.py").touch()
    (tmp_path / "two.py").touch()
    script = r"""
import { readFileSync } from "node:fs";
import { runProcess } from "./dist/pi/extensions/_agentbundler-hooks/index.ts";
const manifest = JSON.parse(readFileSync("./dist/pi/hooks/hooks.v1.json", "utf8"));
const hook = manifest.hooks.find((entry) => entry.identity === "hook/smart-lint");
const result = await runProcess(hook.handler, {
  packageRoot: "./dist/pi",
  input: {
    event: "post-tool",
    hook: hook.identity,
    piEvent: {
      cwd: process.env.HOME,
      session_id: "generated-stdin",
      toolName: "write",
      input: { path: "one.py" },
    },
  },
  timeoutMilliseconds: hook.timeoutMilliseconds,
  environment: hook.environment,
});
console.log(JSON.stringify(result));
"""
    result = subprocess.run(
        ["bun", "-e", script],
        cwd=REPO_ROOT,
        env={**os.environ, "HOME": str(tmp_path), "SKIP_LINT": "1"},
        text=True,
        capture_output=True,
        check=True,
        # Generous outer bound: see the git-guardrails test above.
        timeout=90,
    )
    outcome = json.loads(result.stdout)
    assert outcome["exitCode"] == 0, outcome["stderr"]
    assert json.loads(outcome["stdout"]) == {"decision": "allow"}
    assert "Linting skipped" in outcome["stderr"]
    state = tmp_path / ".git/cc-thingz/hooks-v2/hook-files-generated-stdin"
    assert state.read_text() == "one.py\n"
    assert not (state.parent / "hook-files-default").exists()


def test_generated_pi_advisories_are_visible_without_model_continuation() -> None:
    script = r"""
import { readFileSync } from "node:fs";
import { createPiHookRuntime } from "./dist/pi/extensions/_agentbundler-hooks/index.ts";
const manifest = JSON.parse(readFileSync("./dist/pi/hooks/hooks.v1.json", "utf8"));
const cases = [
  ["hook/test-runner", "advisory"],
  ["hook/test-runner", "runtime-error"],
  ["hook/file-protector", "runtime-error"],
  ["hook/file-protector", "deny"],
];
for (const [identity, mode] of cases) {
  const hook = manifest.hooks.find((value) => value.identity === identity);
  const handlers = new Map();
  const notices = [];
  let modelTurns = 0;
  const pi = {
    on: (event, handler) => handlers.set(event, handler),
    sendUserMessage: () => { modelTurns++; },
    sendMessage: () => { modelTurns++; },
  };
  createPiHookRuntime(pi, { version: 1, hooks: [hook] }, {
    packageRoot: "./dist/pi",
    runner: async () => {
      if (mode === "runtime-error") throw new Error("runtime unavailable");
      return {
        exitCode: 0, signal: null,
        stdout: mode === "deny"
      ? '{"decision":"deny","reason":"protected"}'
      : '{"decision":"allow"}',
        stderr: mode === "advisory" ? "tests incomplete: missing environment" : "",
      };
    },
  });
  const eventName = hook.event === "stop" ? "agent_end" : "tool_call";
  const result = await handlers.get(eventName)(
    { toolName: "write", input: { path: "server.key" } },
    { hasUI: true, ui: { notify: (message, type) => notices.push({ message, type }) } },
  );
  console.log(JSON.stringify({ identity, mode, result, notices, modelTurns }));
}
"""
    proc = subprocess.run(
        ["bun", "-e", script],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    advisory, unavailable, closed, denied = [
        json.loads(line) for line in proc.stdout.splitlines()
    ]
    assert len(advisory["notices"]) == 1
    assert "missing environment" in advisory["notices"][0]["message"]
    assert len(unavailable["notices"]) == 1
    assert "runtime unavailable" in unavailable["notices"][0]["message"]
    assert "result" not in advisory
    assert "result" not in unavailable
    assert closed["result"]["block"] is True
    assert "runtime unavailable" in closed["result"]["reason"]
    assert denied["result"] == {"block": True, "reason": "protected"}
    assert all(
        item["modelTurns"] == 0 for item in (advisory, unavailable, closed, denied)
    )


def test_generated_pi_adapter_uses_project_context_and_session_state(
    tmp_path: Path,
) -> None:
    env = os.environ.copy()
    env["HOME"] = str(tmp_path / "home")
    Path(env["HOME"]).mkdir()
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True, env=env)
    project = tmp_path / "api"
    tests = project / "tests"
    tests.mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "root"\nversion = "0.0.0"\n'
    )
    (project / "pyproject.toml").write_text(
        '[project]\nname = "api"\nversion = "0.0.0"\n'
    )
    (tests / "test_widget.py").write_text("def test_widget(): pass\n")
    tools = project / ".venv/bin"
    tools.mkdir(parents=True)
    for name in ("ruff", "pyright", "pytest"):
        tool = tools / name
        tool.write_text(
            f'#!/bin/sh\nprintf "%s\\n" "$PWD|$*" >>"{project}/{name}.calls"\n'
        )
        tool.chmod(0o755)
    env["HOOK_AUDIT_PROJECT"] = str(tmp_path)
    script = r"""
import adapter from "./dist/pi/extensions/agentbundler-hooks.ts";
const handlers = new Map();
const notices = [];
let modelTurns = 0;
adapter({
  on: (event, handler) => handlers.set(event, handler),
  sendUserMessage: () => { modelTurns++; },
  sendMessage: () => { modelTurns++; },
});
const context = {
  cwd: process.env.HOOK_AUDIT_PROJECT,
  sessionManager: { getSessionId: () => "pi-runtime-session" },
  hasUI: true,
  ui: { notify: (message, type) => notices.push({ message, type }) },
};
await handlers.get("tool_result")({
  toolName: "edit", input: { path: "api/tests/test_widget.py" }, isError: false,
}, context);
await handlers.get("agent_end")({ messages: [] }, context);
console.log(JSON.stringify({ notices, modelTurns }));
"""
    proc = subprocess.run(
        ["bun", "-e", script],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    result = json.loads(proc.stdout)
    assert result["modelTurns"] == 0
    assert (project / "pytest.calls").read_text().strip() == (
        f"{project}|-q --maxfail=1 --tb=short tests/test_widget.py"
    )
    assert "tests/test_widget.py" in (project / "ruff.calls").read_text()
    state = tmp_path / ".git/cc-thingz/hooks-v2/hook-files-pi-runtime-session"
    assert state.is_file()
    assert state.read_text() == ""
    assert not (tmp_path / ".git/cc-thingz/hooks-v2/hook-files-default").exists()
    assert any("Focused tests passed" in item["message"] for item in result["notices"])
