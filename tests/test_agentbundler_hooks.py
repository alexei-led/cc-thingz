"""Agent Bundler hook and Pi compatibility-stack integration contracts."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from conftest import REPO_ROOT

PI_PORTABLE_HOOKS = {
    "hook/session-start",
    "hook/skill-enforcer",
    "hook/file-protector",
    "hook/git-guardrails",
    "hook/smart-lint",
    "hook/test-runner",
}
GUARD_TARGETS = {
    "claude": {"file-protector", "git-guardrails"},
    "codex": {"file-protector", "git-guardrails"},
    "copilot": {"file-protector", "git-guardrails"},
    "cursor": {"git-guardrails"},
    "grok": {"file-protector", "git-guardrails"},
    "pi": {"file-protector", "git-guardrails"},
}


def _build() -> None:
    subprocess.run(["agbun", "build", "--root", str(REPO_ROOT)], check=True)


def _generated_hook_paths(target: str, hook_name: str) -> list[Path]:
    return list((REPO_ROOT / "dist" / target).rglob(hook_name))


def test_agentbundler_renders_pi_portable_and_compatibility_hook_contracts() -> None:
    _build()

    manifest = json.loads((REPO_ROOT / "dist/pi/hooks/hooks.v1.json").read_text())
    hooks = {entry["identity"]: entry for entry in manifest["hooks"]}

    assert set(hooks) == PI_PORTABLE_HOOKS
    assert hooks["hook/file-protector"]["failurePolicy"] == "closed"
    assert hooks["hook/git-guardrails"]["matcher"]["tools"] == ["command"]
    assert (REPO_ROOT / "dist/pi/extensions/agentbundler-hooks.ts").is_file()

    compatibility = json.loads(
        (REPO_ROOT / "dist/pi/extensions/hooks.json").read_text()
    )
    assert set(compatibility["hooks"]) == {
        "Notification",
        "PreToolUse",
        "SessionEnd",
        "SessionStart",
        "Stop",
    }
    assert compatibility["hooks"]["PreToolUse"][0]["matcher"] == "ExitPlanMode"
    assert (
        "revdiff-plan-review.py"
        in compatibility["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
    )
    assert compatibility["hooks"]["Notification"][0]["hooks"][0]["async"] is True
    for event in ("SessionStart", "SessionEnd", "Stop"):
        assert compatibility["hooks"][event][0]["hooks"][0] == {
            "type": "command",
            "command": "ccgram hook",
            "timeout": 5,
            "async": True,
        }
    assert "file-protector" not in json.dumps(compatibility)
    assert "git-guardrails" not in json.dumps(compatibility)
    assert "smart-lint" not in json.dumps(compatibility)
    assert "test-runner" not in json.dumps(compatibility)


def test_agentbundler_renders_target_hook_matrix() -> None:
    _build()

    for target, expected in GUARD_TARGETS.items():
        for hook_name in ("file-protector", "git-guardrails"):
            assert bool(_generated_hook_paths(target, hook_name)) is (
                hook_name in expected
            )

    codex_hooks = json.loads(
        (REPO_ROOT / "dist/codex/dev-flow/hooks/hooks.json").read_text()
    )
    assert (
        codex_hooks["hooks"]["PostToolUse"][0]["matcher"]
        == "^apply_patch$|^Edit$|^Write$"
    )
    assert "smart-lint" in codex_hooks["hooks"]["PostToolUse"][0]["hooks"][0]["command"]

    grok_hooks = json.loads(
        (REPO_ROOT / "dist/grok/dev-flow/hooks/hooks.json").read_text()
    )
    assert (
        "notify-grok/hook.sh"
        in grok_hooks["hooks"]["Notification"][0]["hooks"][0]["args"][0]
    )


def test_generated_pi_runtime_executes_real_git_guard_with_safe_environment(
    tmp_path: Path,
) -> None:
    _build()
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
    timeoutMilliseconds: hook.timeoutMilliseconds,
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
        input='{"event":"pre-tool","piEvent":{"input":{"path":".env"}}}',
        capture_output=True,
        check=True,
        text=True,
    )
    git_guardrails = subprocess.run(
        ["bash", "src/hooks/git-guardrails/hook.sh"],
        cwd=REPO_ROOT,
        input='{"event":"pre-tool","piEvent":{"input":{"command":"git reset --hard"}}}',
        capture_output=True,
        check=True,
        text=True,
    )

    assert json.loads(file_protector.stdout)["decision"] == "deny"
    assert json.loads(git_guardrails.stdout)["decision"] == "deny"
