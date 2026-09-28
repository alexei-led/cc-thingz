#!/usr/bin/env python3
"""SessionStart hook: report project type and spec-flow state as plain text.

Reads {"cwd": "..."} from stdin (Claude Code hook contract). Always exits 0.
Output reaches model context, so it carries no ANSI color or emoji and skips
facts the harness already provides (git branch and status, instruction files).
"""

from __future__ import annotations

import contextlib
import json
import shutil
import subprocess
import sys
from pathlib import Path


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


def _specctl_json(args: list[str], cwd: Path) -> dict | list | None:
    try:
        out = subprocess.run(
            ["specctl", *args, "--json"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
            timeout=2,
        )
    except (
        FileNotFoundError,
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
    ):
        return None
    if not out.stdout.strip():
        return None
    try:
        return json.loads(out.stdout)
    except json.JSONDecodeError:
        return None


def _show_spec_project(cwd: Path) -> None:
    if not (cwd / ".spec").is_dir() or not shutil.which("specctl"):
        return
    print("Spec-driven project (.spec/)")

    status = _specctl_json(["status"], cwd)
    if isinstance(status, dict):
        done = status.get("done", 0)
        total = status.get("total", 0)
        in_prog = status.get("in_progress", 0)
        print(f"Tasks: {done}/{total} done, {in_prog} in progress")

    session = _specctl_json(["session", "show"], cwd)
    if isinstance(session, dict) and session.get("task"):
        task = session["task"]
        step = session.get("step", "?")
        print(f"Session: {task} at {step}; run `specctl session resume`")
        return

    ready = _specctl_json(["ready"], cwd)
    if isinstance(ready, list) and ready:
        print("Ready:")
        for item in ready[:3]:
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
    cwd = _read_cwd(payload)
    if not cwd.is_dir():
        if pi_runtime:
            print('{"decision":"allow"}')
        return 0

    output = sys.stderr if pi_runtime else sys.stdout
    with contextlib.redirect_stdout(output):
        _show_project_hints(cwd)
        _show_spec_project(cwd)
    if pi_runtime:
        print('{"decision":"allow"}')
    return 0


if __name__ == "__main__":
    sys.exit(main())
