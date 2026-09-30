"""SessionStart hook tests."""

from __future__ import annotations

import importlib.util
import io
import json
import os
import select
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

HOOK = (
    Path(__file__).resolve().parent.parent.parent
    / "src"
    / "hooks"
    / "session-start"
    / "hook.py"
)


def _load_hook_module():
    spec = importlib.util.spec_from_file_location("session_start_hook", HOOK)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run(payload: dict | None, cwd: Path | None = None) -> tuple[int, str, str]:
    body = "" if payload is None else json.dumps(payload)
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input=body,
        capture_output=True,
        text=True,
        cwd=cwd or HOOK.parent,
        timeout=60,
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


def test_omits_git_context_and_instruction_file_hints(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    (tmp_path / "README.md").write_text("# x\n")
    (tmp_path / "CLAUDE.md").write_text("# x\n")
    code, out, _ = _run({"cwd": str(tmp_path)})
    assert code == 0
    assert out == ""


def test_project_hints_are_plain_text(tmp_path: Path) -> None:
    (tmp_path / "go.mod").write_text("module x\n")
    (tmp_path / "pyproject.toml").write_text("[project]\n")
    code, out, _ = _run({"cwd": str(tmp_path)})
    assert code == 0
    assert out.splitlines() == ["Go project", "Python project"]
    assert out.isascii()


def test_ignores_legacy_feature_list(tmp_path: Path) -> None:
    (tmp_path / "feature_list.json").write_text('[{"passes": true}]')
    (tmp_path / "claude-progress.txt").write_text("## Current Status: green\n")
    code, out, _ = _run({"cwd": str(tmp_path)})
    assert code == 0
    assert out == ""


def test_spec_project_reports_status_and_ready_tasks(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    # In-process with a generous test-only specctl timeout, decoupled from
    # hook.py's real 3s production ceiling: under CPU load, scheduling delay
    # alone can eat that whole budget before this trivial mock even runs,
    # which has nothing to do with the JSON-formatting behavior under test.
    hook = _load_hook_module()
    monkeypatch.setattr(hook, "SPECCTL_TIMEOUT_SECONDS", 30)
    (tmp_path / ".spec").mkdir()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    specctl = bin_dir / "specctl"
    specctl.write_text(
        "#!/bin/sh\n"
        'case "$1" in\n'
        """status) echo '{"done": 1, "total": 3, "in_progress": 1}' ;;\n"""
        "session) echo '{}' ;;\n"
        """ready) echo '[{"id": "T-2", "priority": "p1", "title": "Add x"}]' ;;\n"""
        "esac\n"
    )
    specctl.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}:/usr/bin:/bin")
    monkeypatch.setattr(
        hook.sys, "stdin", io.StringIO(json.dumps({"cwd": str(tmp_path)}))
    )

    code = hook.main()

    assert code == 0
    assert capsys.readouterr().out.splitlines() == [
        "Spec-driven project (.spec/)",
        "Tasks: 1/3 done, 1 in progress",
        "Ready:",
        "  T-2 [p1] Add x",
    ]


def test_specctl_queries_run_concurrently(tmp_path: Path, monkeypatch) -> None:
    """Sequential calls could exceed the 5 s hook timeout under load.

    Proves concurrency structurally instead of via a wall-clock overlap
    window: each specctl invocation blocks until released, so all 3 must be
    in flight simultaneously before any of them can complete. A timestamp/
    sleep overlap check can't survive CPU load or xdist parallelism, which
    can add several seconds of pure process-scheduling latency to a single
    call regardless of whether hook.py's dispatch is sequential or concurrent.
    """
    hook = _load_hook_module()
    arrival_deadline_sec = 30
    # Must clear the arrival deadline: a shorter timeout would let a
    # sequential implementation "pass" by arriving, getting killed, arriving
    # again, and so on for each of the 3 calls in turn, all before the
    # deadline fires — hiding exactly the bug this test exists to catch.
    monkeypatch.setattr(hook, "SPECCTL_TIMEOUT_SECONDS", arrival_deadline_sec * 2)
    (tmp_path / ".spec").mkdir()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    arrived_dir = tmp_path / "arrived"
    arrived_dir.mkdir()
    release = tmp_path / "release"
    specctl = bin_dir / "specctl"
    specctl.write_text(
        "#!/bin/sh\n"
        f'touch "{arrived_dir}/$1"\n'
        f'while [ ! -f "{release}" ]; do sleep 0.1; done\n'
        "echo '{}'\n"
    )
    specctl.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}:/usr/bin:/bin")

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(hook._show_spec_project, tmp_path)
        try:
            deadline = time.monotonic() + arrival_deadline_sec
            arrived: set[str] = set()
            while time.monotonic() < deadline:
                arrived = {p.name for p in arrived_dir.iterdir()}
                if arrived == {"status", "session", "ready"}:
                    break
                time.sleep(0.1)
            assert arrived == {"status", "session", "ready"}, (
                f"only {arrived or 'none'} arrived within {arrival_deadline_sec}s "
                "— dispatch looks sequential, not concurrent"
            )
        finally:
            release.touch()
            future.result(timeout=arrival_deadline_sec)


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
        timeout=60,
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
        timeout=60,
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
    stdout pipe and this would hang past the timeout.

    Measures from the hook process's own exit, not overall wall-clock: once
    the parent has exited, EOF on its stdout pipe depends only on kernel
    file-descriptor state (whether a detached child still holds the write end
    open), not on anything that needs to be scheduled — so a short bound
    holds under any CPU load, unlike a fixed bound on the whole run.
    """
    proc = subprocess.Popen(
        [sys.executable, str(HOOK)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=tmp_path,
    )
    proc.stdin.write(json.dumps({"cwd": str(tmp_path)}))
    proc.stdin.close()
    proc.wait(timeout=60)

    assert proc.returncode == 0
    # Output is empty for this bare cwd, so reading after wait() can't
    # deadlock on a full pipe buffer.
    ready, _, _ = select.select([proc.stdout], [], [], 2)
    assert ready, "stdout not at EOF within 2s of the hook process exiting"
    assert proc.stdout.read() == ""
