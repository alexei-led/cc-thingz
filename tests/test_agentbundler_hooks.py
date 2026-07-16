"""Agent Bundler hook integration contracts for the cc-thingz bundle."""

from __future__ import annotations

import json
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
