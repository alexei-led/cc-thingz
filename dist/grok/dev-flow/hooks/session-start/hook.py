#!/usr/bin/env python3
"""SessionStart hook — initialize agent with project context.

Reads {"cwd": "..."} from stdin (Claude Code hook contract). Always exits 0;
diagnostic output goes to stdout for the user to see at session start.
"""

from __future__ import annotations

import contextlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

BLUE = "\033[0;34m"
GREEN = "\033[0;32m"
YELLOW = "\033[0;33m"
CYAN = "\033[0;36m"
NC = "\033[0m"


def _say(color: str, label: str, body: str = "") -> None:
    sep = " " if body else ""
    print(f"{color}{label}{NC}{sep}{body}")


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


def _git(args: list[str], cwd: Path) -> str | None:
    try:
        out = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
            timeout=4,
        )
    except (
        FileNotFoundError,
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
    ):
        return None
    return out.stdout.strip()


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


def _cleanup_old_files() -> None:
    """Best-effort retention sweep. Errors are silenced."""
    home = Path.home()
    now = time.time()
    week = 7 * 86400
    month = 30 * 86400

    def _sweep(root: Path, max_age: float, gzip: bool = False) -> None:
        if not root.is_dir():
            return
        for p in root.rglob("*"):
            if not p.is_file():
                continue
            try:
                if now - p.stat().st_mtime <= max_age:
                    continue
                if gzip and p.suffix == ".md":
                    subprocess.run(
                        ["gzip", str(p)],
                        check=False,
                        stderr=subprocess.DEVNULL,
                    )
                else:
                    p.unlink()
            except OSError:
                continue

    _sweep(home / ".claude" / "todos", week)
    _sweep(home / ".claude" / "debug", month)
    _sweep(home / ".claude" / "plans", month, gzip=True)


def _show_git(cwd: Path) -> None:
    if not (cwd / ".git").is_dir():
        return
    branch = _git(["branch", "--show-current"], cwd) or "detached"
    last = _git(["log", "--oneline", "-1"], cwd) or "no commits"
    _say(BLUE, "🌿 Branch:", branch)
    _say(BLUE, "📝 Last:", last)


def _show_spec_project(cwd: Path) -> None:
    if not (cwd / ".spec").is_dir() or not shutil.which("specctl"):
        return
    print()
    _say(CYAN, "📋 Spec-Driven Project")

    status = _specctl_json(["status"], cwd)
    if isinstance(status, dict):
        done = status.get("done", 0)
        total = status.get("total", 0)
        in_prog = status.get("in_progress", 0)
        _say(GREEN, "📊 Tasks:", f"{done}/{total} done, {in_prog} in progress")

    session = _specctl_json(["session", "show"], cwd)
    if isinstance(session, dict) and session.get("task"):
        task = session["task"]
        step = session.get("step", "?")
        _say(YELLOW, "⚠️  Session:", f"{task} at {step} — run `specctl session resume`")
        return

    ready = _specctl_json(["ready"], cwd)
    if isinstance(ready, list) and ready:
        _say(GREEN, "✅ Ready:")
        for item in ready[:3]:
            print(f"    {item.get('id')} [{item.get('priority')}] {item.get('title')}")


def _show_feature_list(cwd: Path) -> bool:
    fl = cwd / "feature_list.json"
    if not fl.is_file():
        return False
    print()
    _say(CYAN, "📋 Spec-Driven Project")

    try:
        features = json.loads(fl.read_text())
    except (OSError, json.JSONDecodeError):
        features = None

    if isinstance(features, list) and features:
        passing = sum(1 for f in features if f.get("passes") is True)
        total = len(features)
        if total:
            pct = passing * 100 // total
            _say(GREEN, "📊 Features:", f"{passing}/{total} passing ({pct}%)")

    progress = cwd / "claude-progress.txt"
    if progress.is_file():
        print()
        _say(YELLOW, "📝 Progress Notes:")
        try:
            text = progress.read_text(errors="replace")
        except OSError:
            text = ""
        markers = (
            "## Current Status:",
            "## Session",
            "Priority features",
            "What to work on next",
        )
        hits = [
            line.rstrip()
            for line in text.splitlines()
            if any(m in line for m in markers)
        ][:5]
        if hits:
            print("\n".join(hits))
        elif text:
            print("\n".join(text.splitlines()[:8]))

    if (cwd / ".git").is_dir():
        status = _git(["status", "--porcelain"], cwd)
        if status:
            n = len([line for line in status.splitlines() if line])
            print()
            _say(YELLOW, "⚠️  Uncommitted changes:", f"{n} files")
    return True


def _show_project_hints(cwd: Path) -> None:
    hints = [
        ("go.mod", CYAN, "🐹 Go project"),
        ("package.json", CYAN, "📦 Node.js project"),
        ("pyproject.toml", CYAN, "🐍 Python project"),
        ("Cargo.toml", CYAN, "🦀 Rust project"),
        ("build.gradle.kts", CYAN, "☕ JVM Gradle project"),
        ("build.gradle", CYAN, "☕ JVM Gradle project"),
        ("pom.xml", CYAN, "☕ JVM Maven project"),
        ("README.md", BLUE, "📖 README.md available"),
        ("CLAUDE.md", BLUE, "🤖 CLAUDE.md available"),
    ]
    for name, color, label in hints:
        if (cwd / name).is_file():
            _say(color, label)


def main() -> int:
    if "--cleanup" in sys.argv[1:]:
        _cleanup_old_files()
        return 0

    payload = _read_payload()
    pi_runtime = payload.get("event") == "session-start" and isinstance(
        payload.get("piEvent"), dict
    )
    cwd = _read_cwd(payload)
    if not cwd.is_dir():
        if pi_runtime:
            print('{"decision":"allow"}')
        return 0

    # Cleanup runs in a detached subprocess instead of via os.fork(): the
    # forked child inherited this process's stdout pipe, so hook runners
    # waiting for EOF (not just process exit) were unbounded by their
    # timeout — the pipe stayed open until the child's sweep finished.
    try:
        subprocess.Popen(
            [sys.executable or "python3", os.path.abspath(__file__), "--cleanup"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            close_fds=True,
        )
    except OSError:
        pass  # Skip background cleanup; session start still succeeds.

    output = sys.stderr if pi_runtime else sys.stdout
    with contextlib.redirect_stdout(output):
        _show_git(cwd)
        if not _show_feature_list(cwd):
            _show_spec_project(cwd)
            _show_project_hints(cwd)
    if pi_runtime:
        print('{"decision":"allow"}')
    return 0


if __name__ == "__main__":
    sys.exit(main())
