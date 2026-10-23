#!/usr/bin/env python3
"""SessionStart hook: report project type and spec-flow state as plain text.

Reads {"cwd": "..."} from stdin (Claude Code hook contract). Always exits 0.
Output reaches model context, so it carries no ANSI color or emoji and skips
facts the harness already provides (git branch and status, instruction files).
"""

from __future__ import annotations

import contextlib
import json
import os
import selectors
import shutil
import signal
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# The three specctl reads run concurrently, each capped at this, so the hook
# stays inside its 5 s SessionStart timeout; three sequential 2 s calls could not.
SPECCTL_TIMEOUT_SECONDS = 3
SPECCTL_OUTPUT_LIMIT_BYTES = 64 * 1024


def _read_payload() -> dict[str, object]:
    if sys.stdin.isatty():
        return {}
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_cwd(payload: dict[str, object]) -> Path:
    pi_event = payload.get("piEvent")
    if isinstance(pi_event, dict):
        cwd = pi_event.get("cwd") or ""
    else:
        cwd = payload.get("cwd") or ""
    return Path(cwd) if isinstance(cwd, str) and cwd else Path.cwd()


def _incomplete(reason: str) -> None:
    print(f"Session context incomplete: {reason}", file=sys.stderr)


def _stop_query(proc: subprocess.Popen) -> None:
    if os.name == "posix":
        with contextlib.suppress(ProcessLookupError):
            os.killpg(proc.pid, signal.SIGKILL)
    elif proc.poll() is None:
        proc.kill()
    proc.wait()


def _specctl_json(args: list[str], cwd: Path) -> dict | list | None:
    try:
        proc = subprocess.Popen(
            ["specctl", *args, "--json"],
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            start_new_session=os.name == "posix",
        )
        raw = bytearray()
        try:
            assert proc.stdout is not None
            with proc.stdout, selectors.DefaultSelector() as selector:
                selector.register(proc.stdout, selectors.EVENT_READ)
                deadline = time.monotonic() + SPECCTL_TIMEOUT_SECONDS
                while True:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0 or not selector.select(remaining):
                        raise subprocess.TimeoutExpired(
                            proc.args, SPECCTL_TIMEOUT_SECONDS
                        )
                    chunk = os.read(proc.stdout.fileno(), 8192)
                    if not chunk:
                        break
                    raw.extend(chunk)
                    if len(raw) > SPECCTL_OUTPUT_LIMIT_BYTES:
                        raise ValueError("output exceeds 64 KiB")
                proc.wait(timeout=max(0, deadline - time.monotonic()))
            if proc.returncode != 0:
                _incomplete(f"specctl {args[0]} exited {proc.returncode}")
                return None
        finally:
            _stop_query(proc)
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        _incomplete(f"specctl {args[0]} unavailable: {error}")
        return None
    if not raw.strip():
        return None
    try:
        data = json.loads(raw)
    except (ValueError, UnicodeError):
        _incomplete(f"specctl {args[0]} returned invalid JSON")
        return None
    if not isinstance(data, (dict, list)):
        _incomplete(f"specctl {args[0]} returned an unexpected result")
        return None
    return data


def _show_spec_project(cwd: Path) -> None:
    if not (cwd / ".spec").is_dir() or not shutil.which("specctl"):
        return
    print("Spec-driven project (.spec/)")

    queries = (["status"], ["session", "show"], ["ready"])
    with ThreadPoolExecutor(max_workers=len(queries)) as pool:
        status, session, ready = pool.map(
            lambda args: _specctl_json(args, cwd), queries
        )
    if isinstance(status, dict):
        done = status.get("done", 0)
        total = status.get("total", 0)
        in_prog = status.get("in_progress", 0)
        print(f"Tasks: {done}/{total} done, {in_prog} in progress")

    if isinstance(session, dict) and session.get("task"):
        task = session["task"]
        step = session.get("step", "?")
        print(f"Session: {task} at {step}; run `specctl session resume`")
        return

    if isinstance(ready, list) and ready:
        print("Ready:")
        for item in ready[:3]:
            if not isinstance(item, dict):
                _incomplete("specctl ready contains an invalid task entry")
                continue
            print(f"  {item.get('id')} [{item.get('priority')}] {item.get('title')}")


PROJECT_MARKERS = (
    ("go.mod", "Go project"),
    ("package.json", "Node.js project"),
    ("pyproject.toml", "Python project"),
    ("Cargo.toml", "Rust project"),
    ("build.gradle.kts", "JVM Gradle project"),
    ("build.gradle", "JVM Gradle project"),
    ("pom.xml", "JVM Maven project"),
)


def _show_project_hints(cwd: Path) -> None:
    for name, label in PROJECT_MARKERS:
        if (cwd / name).is_file():
            print(label)


def main() -> int:
    payload = _read_payload()
    pi_runtime = payload.get("event") == "session-start" and isinstance(
        payload.get("piEvent"), dict
    )
    try:
        cwd = _read_cwd(payload)
        if cwd.is_dir():
            output = sys.stderr if pi_runtime else sys.stdout
            with contextlib.redirect_stdout(output):
                _show_project_hints(cwd)
                _show_spec_project(cwd)
    except Exception as error:
        # This advisory boundary must not turn context discovery into a gate.
        _incomplete(f"{type(error).__name__}: {error}")
    if pi_runtime:
        print('{"decision":"allow"}')
    return 0


if __name__ == "__main__":
    sys.exit(main())
