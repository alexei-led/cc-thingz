"""Agent Bundler hook integration contracts for the cc-thingz bundle."""

from __future__ import annotations

import json
import os
import subprocess

from conftest import REPO_ROOT


def _build() -> None:
    subprocess.run(["agbun", "build", "--root", str(REPO_ROOT)], check=True)


def test_agentbundler_renders_pi_aggregate_hook_runtime() -> None:
    _build()

    manifest = json.loads((REPO_ROOT / "dist/pi/hooks/hooks.v1.json").read_text())
    hooks = {entry["identity"]: entry for entry in manifest["hooks"]}

    assert set(hooks) == {
        "hook/session-start",
        "hook/skill-enforcer",
        "hook/file-protector",
        "hook/git-guardrails",
        "hook/smart-lint",
        "hook/test-runner",
    }
    assert hooks["hook/file-protector"]["failurePolicy"] == "closed"
    assert hooks["hook/git-guardrails"]["matcher"]["tools"] == ["command"]
    assert (REPO_ROOT / "dist/pi/extensions/agentbundler-hooks.ts").is_file()


def test_generated_pi_runtime_executes_real_git_guard_with_safe_environment(
    tmp_path,
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


def test_agentbundler_keeps_pi_decision_guards_off_portable_targets() -> None:
    _build()

    for target in ("claude", "codex", "copilot", "cursor", "grok"):
        paths = list((REPO_ROOT / "dist" / target).rglob("file-protector"))
        assert paths == []
        paths = list((REPO_ROOT / "dist" / target).rglob("git-guardrails"))
        assert paths == []


def test_unbundled_lifecycle_hooks_are_explicit() -> None:
    unsupported = (REPO_ROOT / "src/hooks/UNSUPPORTED.md").read_text()

    for name in ("revdiff-plan-review", "worktree-create", "worktree-remove"):
        assert name in unsupported
        assert (REPO_ROOT / "src/hooks" / name).is_dir()
        assert not any((REPO_ROOT / "dist").rglob(name))


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
