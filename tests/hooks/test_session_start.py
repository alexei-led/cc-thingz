"""SessionStart hook tests.

Replaces the old bats test, which only covered "exit 0 on valid/empty input".
Adds coverage for git context, .spec/, feature_list.json, and project-hint
branches that the bats test left untouched.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import pytest

HOOK = (
    Path(__file__).resolve().parent.parent.parent
    / "src"
    / "hooks"
    / "session-start"
    / "hook.py"
)

ANSI = re.compile(r"\x1b\[[0-9;]*m")


def _strip(s: str) -> str:
    return ANSI.sub("", s)


def _run(payload: dict | None, cwd: Path | None = None) -> tuple[int, str, str]:
    body = "" if payload is None else json.dumps(payload)
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input=body,
        capture_output=True,
        text=True,
        cwd=cwd or HOOK.parent,
        timeout=5,
    )
    return proc.returncode, proc.stdout, proc.stderr


def test_valid_cwd_exits_zero(tmp_path: Path) -> None:
    code, _, _ = _run({"cwd": str(tmp_path)})
    assert code == 0


def test_empty_payload_exits_zero(tmp_path: Path) -> None:
    code, _, _ = _run({}, cwd=tmp_path)
    assert code == 0


def test_invalid_cwd_exits_zero(tmp_path: Path) -> None:
    """Non-existent cwd must not abort the hook."""
    bogus = tmp_path / "does-not-exist"
    code, _, _ = _run({"cwd": str(bogus)})
    assert code == 0


def test_git_context_displayed(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.email=t@t",
            "-c",
            "user.name=t",
            "commit",
            "--allow-empty",
            "-m",
            "init",
        ],
        cwd=tmp_path,
        check=True,
    )
    code, out, _ = _run({"cwd": str(tmp_path)})
    assert code == 0
    plain = _strip(out)
    assert "Branch:" in plain
    assert "Last:" in plain


def test_feature_list_branch_used_when_present(tmp_path: Path) -> None:
    (tmp_path / "feature_list.json").write_text(
        json.dumps([{"name": "a", "passes": True}, {"name": "b", "passes": False}])
    )
    code, out, _ = _run({"cwd": str(tmp_path)})
    assert code == 0
    plain = _strip(out)
    assert "Spec-Driven Project" in plain
    assert "Features: 1/2 passing" in plain


def test_progress_notes_when_feature_list_present(tmp_path: Path) -> None:
    (tmp_path / "feature_list.json").write_text("[]")
    (tmp_path / "claude-progress.txt").write_text(
        "## Current Status: green\nfoo\n## Session 1\nbar\n"
    )
    code, out, _ = _run({"cwd": str(tmp_path)})
    assert code == 0
    plain = _strip(out)
    assert "Progress Notes:" in plain
    assert "## Current Status: green" in plain


def test_project_hints_when_no_feature_list(tmp_path: Path) -> None:
    (tmp_path / "go.mod").write_text("module x\n")
    (tmp_path / "README.md").write_text("# x\n")
    code, out, _ = _run({"cwd": str(tmp_path)})
    assert code == 0
    plain = _strip(out)
    assert "Go project" in plain
    assert "README.md available" in plain


def test_spec_branch_skipped_without_specctl(tmp_path: Path) -> None:
    """`.spec/` exists but `specctl` is missing on PATH — must not crash."""
    (tmp_path / ".spec").mkdir()
    env = os.environ.copy()
    env["PATH"] = "/usr/bin:/bin"
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps({"cwd": str(tmp_path)}),
        capture_output=True,
        text=True,
        env=env,
        timeout=5,
    )
    assert proc.returncode == 0


@pytest.mark.parametrize("body", ["not json", "{", "null"])
def test_malformed_stdin_does_not_crash(body: str, tmp_path: Path) -> None:
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input=body,
        capture_output=True,
        text=True,
        cwd=tmp_path,
        timeout=5,
    )
    assert proc.returncode == 0


@pytest.mark.parametrize("pi_runtime", [False, True])
def test_start_preserves_global_artifacts(tmp_path, monkeypatch, pi_runtime):
    monkeypatch.setenv("HOME", str(tmp_path))
    paths = [
        tmp_path / ".claude" / name
        for name in (
            "todos/old.json",
            "debug/old.log",
            "plans/old.md",
            "plans/old.md.gz",
        )
    ]
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"keep these bytes")
        os.utime(path, (1, 1))
    before = {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in paths}
    payload = {"cwd": str(tmp_path)}
    if pi_runtime:
        payload = {"event": "session-start", "piEvent": payload}
    code, _, _ = _run(payload)
    assert code == 0
    assert {
        path: (path.read_bytes(), path.stat().st_mtime_ns) for path in paths
    } == before


def test_stdout_reaches_eof_promptly(tmp_path: Path) -> None:
    """End-to-end smoke: a caller reading stdout to EOF must not block on the
    detached cleanup subprocess. Pre-fix (os.fork()), the child inherited the
    stdout pipe and this would hang past the timeout."""
    proc = subprocess.Popen(
        [sys.executable, str(HOOK)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=tmp_path,
    )
    start = time.monotonic()
    proc.communicate(input=json.dumps({"cwd": str(tmp_path)}), timeout=2)
    elapsed = time.monotonic() - start

    assert proc.returncode == 0
    assert elapsed < 2
