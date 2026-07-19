from __future__ import annotations

import importlib.util
import io
import json
import subprocess
import sys

import pytest
from conftest import REPO_ROOT

MODULE_PATH = (
    REPO_ROOT
    / "src"
    / "plugins"
    / "pi"
    / "extensions"
    / "hooks"
    / "revdiff-plan-review.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "revdiff_plan_review_hook", MODULE_PATH
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_adapt_response_converts_upstream_ask_to_allow():
    hook = load_module()
    raw = json.dumps(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "ask",
                "permissionDecisionReason": "plan reviewed, no annotations",
            }
        }
    )

    output = json.loads(hook.adapt_response_for_pi(raw))

    assert output["hookSpecificOutput"]["permissionDecision"] == "allow"
    assert (
        output["hookSpecificOutput"]["permissionDecisionReason"]
        == "plan reviewed, no annotations"
    )


def test_adapt_response_leaves_other_output_unchanged():
    hook = load_module()
    outputs = [
        "",
        "not json",
        json.dumps({"hookSpecificOutput": {"permissionDecision": "allow"}}),
        json.dumps({"hookSpecificOutput": {"permissionDecision": "deny"}}),
    ]

    assert [hook.adapt_response_for_pi(output) for output in outputs] == outputs


def test_no_plugin_found_exits_zero(monkeypatch, tmp_path):
    hook = load_module()
    monkeypatch.setenv("PI_CODING_AGENT_DIR", str(tmp_path / "agent"))
    monkeypatch.delenv("PI_PACKAGE_DIR", raising=False)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.stdin", io.StringIO(""))

    with pytest.raises(SystemExit) as exc:
        hook.main()

    assert exc.value.code == 0


def test_candidate_roots_include_project_and_agent_dirs(monkeypatch, tmp_path):
    hook = load_module()
    agent = tmp_path / "agent"
    monkeypatch.setenv("PI_CODING_AGENT_DIR", str(agent))
    monkeypatch.delenv("PI_PACKAGE_DIR", raising=False)
    monkeypatch.chdir(tmp_path)

    roots = hook.candidate_roots()

    assert (
        tmp_path
        / ".pi"
        / "git"
        / "github.com"
        / "umputun"
        / "revdiff"
        / "plugins"
        / "revdiff-planning"
        in roots
    )
    assert (
        agent
        / "git"
        / "github.com"
        / "umputun"
        / "revdiff"
        / "plugins"
        / "revdiff-planning"
        in roots
    )


def test_resolve_timeout_uses_env_var_with_kill_margin(monkeypatch):
    hook = load_module()
    monkeypatch.setenv("PI_HOOK_TIMEOUT_SEC", "600")
    # Subprocess timeout sits below the parent kill so the child exits with a
    # blocking message before SIGKILL.
    assert hook.resolve_timeout() == 600 - hook._PARENT_KILL_MARGIN_SEC


def test_resolve_timeout_falls_back_when_env_missing_or_garbage(monkeypatch):
    hook = load_module()
    monkeypatch.delenv("PI_HOOK_TIMEOUT_SEC", raising=False)
    assert hook.resolve_timeout() == hook._FALLBACK_TIMEOUT_SEC

    monkeypatch.setenv("PI_HOOK_TIMEOUT_SEC", "not-a-number")
    assert hook.resolve_timeout() == hook._FALLBACK_TIMEOUT_SEC

    monkeypatch.setenv("PI_HOOK_TIMEOUT_SEC", "0")
    assert hook.resolve_timeout() == hook._FALLBACK_TIMEOUT_SEC

    monkeypatch.setenv("PI_HOOK_TIMEOUT_SEC", "-7")
    assert hook.resolve_timeout() == hook._FALLBACK_TIMEOUT_SEC


def test_resolve_timeout_clamps_short_parent_to_one(monkeypatch):
    hook = load_module()
    monkeypatch.setenv("PI_HOOK_TIMEOUT_SEC", "1")
    # 1 - margin would go below 1; clamp keeps a non-zero positive timeout.
    assert hook.resolve_timeout() == 1


def test_main_fails_open_when_upstream_script_raises_oserror(monkeypatch, tmp_path):
    """Permission errors or missing interpreters fall into the same bucket as
    'plugin not installed' — block exit would punish operators for a flaky
    install instead of letting the plan proceed."""
    hook = load_module()
    plugin_root = (
        tmp_path
        / "agent"
        / "git"
        / "github.com"
        / "umputun"
        / "revdiff"
        / "plugins"
        / "revdiff-planning"
    )
    script = plugin_root / "scripts" / "plan-review-hook.py"
    script.parent.mkdir(parents=True)
    script.write_text("")
    monkeypatch.setenv("PI_CODING_AGENT_DIR", str(tmp_path / "agent"))
    monkeypatch.delenv("PI_PACKAGE_DIR", raising=False)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(hook.sys, "stdin", io.StringIO(""))

    def boom(*_args, **_kwargs):
        raise OSError("permission denied")

    monkeypatch.setattr(hook.subprocess, "run", boom)

    with pytest.raises(SystemExit) as exc:
        hook.main()

    assert exc.value.code == 0


def test_main_fails_open_when_upstream_subprocess_error(monkeypatch, tmp_path):
    hook = load_module()
    plugin_root = (
        tmp_path
        / "agent"
        / "git"
        / "github.com"
        / "umputun"
        / "revdiff"
        / "plugins"
        / "revdiff-planning"
    )
    script = plugin_root / "scripts" / "plan-review-hook.py"
    script.parent.mkdir(parents=True)
    script.write_text("")
    monkeypatch.setenv("PI_CODING_AGENT_DIR", str(tmp_path / "agent"))
    monkeypatch.delenv("PI_PACKAGE_DIR", raising=False)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(hook.sys, "stdin", io.StringIO(""))

    def boom(*_args, **_kwargs):
        raise subprocess.SubprocessError("upstream blew up")

    monkeypatch.setattr(hook.subprocess, "run", boom)

    with pytest.raises(SystemExit) as exc:
        hook.main()

    assert exc.value.code == 0


def test_end_to_end_fail_open_when_revdiff_absent(tmp_path):
    """True e2e: run the hook script as a real subprocess with an empty
    agent dir (no revdiff anywhere on disk). Exit must be 0 so plan-mode
    proceeds without blocking."""
    agent_dir = tmp_path / "agent"
    agent_dir.mkdir()
    result = subprocess.run(
        [sys.executable, str(MODULE_PATH)],
        input="",
        capture_output=True,
        text=True,
        timeout=15,
        env={
            "PATH": "/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin",
            "PI_CODING_AGENT_DIR": str(agent_dir),
            # Force HOME to a path without ~/.pi so the agent_dir() fallback
            # can't accidentally find a real revdiff install.
            "HOME": str(tmp_path),
        },
        cwd=str(tmp_path),
    )
    assert result.returncode == 0, (
        f"fail-open expected, got rc={result.returncode}, stderr={result.stderr}"
    )


def test_main_invokes_plugin_and_converts_ask_to_allow(monkeypatch, tmp_path, capsys):
    hook = load_module()
    plugin_root = (
        tmp_path
        / "agent"
        / "git"
        / "github.com"
        / "umputun"
        / "revdiff"
        / "plugins"
        / "revdiff-planning"
    )
    script = plugin_root / "scripts" / "plan-review-hook.py"
    script.parent.mkdir(parents=True)
    script.write_text("#!/usr/bin/env python3\n")
    monkeypatch.setenv("PI_CODING_AGENT_DIR", str(tmp_path / "agent"))
    monkeypatch.delenv("PI_PACKAGE_DIR", raising=False)
    monkeypatch.chdir(tmp_path)

    def fake_run(*args, **kwargs):
        assert args[0][1] == str(script)
        assert kwargs["env"]["CLAUDE_PLUGIN_ROOT"] == str(plugin_root)
        assert "PYTHONPATH" not in kwargs["env"]
        return subprocess.CompletedProcess(
            args=args[0],
            returncode=0,
            stdout=json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "ask",
                    }
                }
            ),
            stderr="",
        )

    monkeypatch.setattr(hook.subprocess, "run", fake_run)
    monkeypatch.setattr(hook.sys, "stdin", io.StringIO(""))

    with pytest.raises(SystemExit) as exc:
        hook.main()

    assert exc.value.code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["hookSpecificOutput"]["permissionDecision"] == "allow"
