"""Cancellation must stop advisory tools, not just their parent hook."""

from __future__ import annotations

import contextlib
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest
from conftest import REPO_ROOT


@pytest.mark.parametrize("hook_name", ["test-runner", "smart-lint"])
def test_cancelled_advisory_hook_stops_its_tool_group(
    tmp_path: Path, hook_name: str
) -> None:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    extension = "go" if hook_name == "test-runner" else "py"
    source = f"one.{extension}"
    (tmp_path / source).touch()
    (tmp_path / "pyproject.toml").touch()
    state = tmp_path / ".git/cc-thingz/hooks-v2/hook-files-cancel"
    state.parent.mkdir(parents=True)
    state.write_text(source + "\n")
    tool = bin_dir / ("go" if hook_name == "test-runner" else "ruff")
    tool.write_text(
        '#!/bin/sh\nsleep 30 &\nchild=$!\nprintf "%s\\n" "$child" >child.pid\nwait\n'
    )
    tool.chmod(0o755)
    payload = {"cwd": str(tmp_path), "session_id": "cancel"}
    if hook_name == "smart-lint":
        payload["tool_input"] = {"file_path": source}
    hook = REPO_ROOT / "src/hooks" / hook_name / "hook.sh"
    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"}
    proc = subprocess.Popen(
        ["bash", str(hook)],
        cwd=tmp_path,
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    assert proc.stdin is not None
    proc.stdin.write(json.dumps(payload))
    proc.stdin.close()
    proc.stdin = None
    child_group = None
    try:
        deadline = time.monotonic() + 30
        pid_file = tmp_path / "child.pid"
        child_pid = None
        while time.monotonic() < deadline:
            if pid_file.exists() and pid_file.read_text().strip().isdigit():
                child_pid = int(pid_file.read_text().strip())
                if child_pid > 0:
                    break
            time.sleep(0.01)
        assert child_pid is not None and child_pid > 0, "tool never became ready"
        child_group = os.getpgid(child_pid)
        assert child_group != os.getpgrp()
        os.killpg(proc.pid, signal.SIGTERM)
        proc.communicate(timeout=10)
        deadline = time.monotonic() + 5
        running = True
        while time.monotonic() < deadline:
            status = subprocess.run(
                ["ps", "-o", "stat=", "-p", str(child_pid)],
                capture_output=True,
                text=True,
                check=False,
            ).stdout.strip()
            running = bool(status) and not status.startswith("Z")
            if not running:
                break
            time.sleep(0.02)
        assert not running, "cancelled hook left its tool running"
        assert source in state.read_text()
    finally:
        if proc.poll() is None:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(proc.pid, signal.SIGKILL)
        if child_group is not None:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(child_group, signal.SIGKILL)
        proc.communicate(timeout=10)


@pytest.mark.parametrize("hook_name", ["test-runner", "smart-lint"])
def test_advisory_hook_caps_tool_output_and_terminates_the_tool(
    tmp_path: Path, hook_name: str
) -> None:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    source = "one.go" if hook_name == "test-runner" else "one.py"
    (tmp_path / source).touch()
    (tmp_path / "pyproject.toml").touch()
    state = tmp_path / ".git/cc-thingz/hooks-v2/hook-files-overflow"
    state.parent.mkdir(parents=True)
    state.write_text(source + "\n")
    tool = bin_dir / ("go" if hook_name == "test-runner" else "ruff")
    tool.write_text(
        f"#!{sys.executable}\nimport os, pathlib, sys, time\n"
        'pathlib.Path("tool.group").write_text(str(os.getpgrp()))\n'
        'sys.stdout.buffer.write(b"x" * (2 * 1024 * 1024))\n'
        "sys.stdout.buffer.flush()\ntime.sleep(30)\n"
    )
    tool.chmod(0o755)
    payload = {"cwd": str(tmp_path), "session_id": "overflow"}
    if hook_name == "smart-lint":
        payload["tool_input"] = {"file_path": source}
    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"}
    proc = subprocess.Popen(
        ["bash", str(REPO_ROOT / "src/hooks" / hook_name / "hook.sh")],
        cwd=tmp_path,
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        out, err = proc.communicate(json.dumps(payload), timeout=15)
        assert proc.returncode == 0
        assert len((out + err).encode()) < 32_000
        assert "exceeded" in err
        assert "Focused tests passed" not in err
        assert "Style OK" not in err
        assert source in state.read_text()
    finally:
        if proc.poll() is None:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(proc.pid, signal.SIGKILL)
        group_file = tmp_path / "tool.group"
        if group_file.exists():
            group = int(group_file.read_text())
            assert group != os.getpgrp()
            with contextlib.suppress(ProcessLookupError):
                os.killpg(group, signal.SIGKILL)
        proc.communicate(timeout=10)


def test_parallel_edits_do_not_overwrite_each_others_pending_files(
    tmp_path: Path,
) -> None:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "one.py").touch()
    (tmp_path / "two.py").touch()
    state = tmp_path / ".git/cc-thingz/hooks-v2/hook-files-parallel"
    state.parent.mkdir(parents=True)
    state.touch()
    barrier = tmp_path / "barrier"
    barrier.mkdir()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    real_cat = shutil.which("cat")
    assert real_cat
    cat = bin_dir / "cat"
    cat.write_text(
        "#!/bin/sh\n"
        'case "$*" in\n*hook-files-parallel)\n'
        f'  "{real_cat}" "$1" >"$BARRIER/cached.$$"\n'
        '  touch "$BARRIER/ready.$$"\n'
        '  while [ ! -f "$BARRIER/release" ]; do sleep 0.01; done\n'
        f'  exec "{real_cat}" "$BARRIER/cached.$$" ;;\n'
        f'*) exec "{real_cat}" "$@" ;;\nesac\n'
    )
    cat.chmod(0o755)
    env = {
        **os.environ,
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "BARRIER": str(barrier),
        "SKIP_LINT": "1",
    }
    processes = []
    try:
        for name in ("one.py", "two.py"):
            proc = subprocess.Popen(
                ["bash", str(REPO_ROOT / "src/hooks/smart-lint/hook.sh")],
                cwd=tmp_path,
                env=env,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            processes.append(proc)
            assert proc.stdin is not None
            proc.stdin.write(
                json.dumps(
                    {
                        "cwd": str(tmp_path),
                        "session_id": "parallel",
                        "tool_input": {"file_path": name},
                    }
                )
            )
            proc.stdin.close()
            proc.stdin = None
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if len(list(barrier.glob("ready.*"))) == 2:
                break
            if all(proc.poll() is not None for proc in processes):
                break
            time.sleep(0.01)
        (barrier / "release").touch()
        for proc in processes:
            _, err = proc.communicate(timeout=10)
            assert proc.returncode == 0, err
        assert set(state.read_text().splitlines()) == {"one.py", "two.py"}
    finally:
        (barrier / "release").touch()
        for proc in processes:
            if proc.poll() is None:
                proc.kill()
            proc.communicate(timeout=10)
