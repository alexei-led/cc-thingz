from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import REPO_ROOT

HOOK = REPO_ROOT / "src/hooks/release-guard/hook.py"
HOOK_CONFIG = REPO_ROOT / "src/hooks/release-guard/hook.json"
LAUNCHER = REPO_ROOT / "src/hooks/release-guard/hook.sh"
TAG = "v6.13.0"
REPOSITORY = "alexei-led/cc-thingz"


def _command(notes_file: Path, *extra: str) -> str:
    arguments = [
        "gh",
        "release",
        "create",
        TAG,
        "--repo",
        REPOSITORY,
        "--verify-tag",
        "--title",
        TAG,
        "--notes-file",
        str(notes_file),
        *extra,
    ]
    return shlex.join(arguments)


def _run_hook(
    command: str, *, enabled: bool = True, pi_runtime: bool = False
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    if enabled:
        environment["HOOK_RELEASE_GUARD"] = "1"
    else:
        environment.pop("HOOK_RELEASE_GUARD", None)
    payload = (
        {"event": "pre-tool", "piEvent": {"input": {"command": command}}}
        if pi_runtime
        else {"tool_name": "Bash", "tool_input": {"command": command}}
    )
    return subprocess.run(
        [sys.executable, str(HOOK)],
        cwd=REPO_ROOT,
        env=environment,
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=False,
    )


def test_release_guard_is_opt_in(tmp_path: Path) -> None:
    result = _run_hook(_command(tmp_path / "missing.md"), enabled=False)

    assert result.returncode == 0
    assert not result.stdout
    assert not result.stderr


def _run_launcher(tmp_path: Path, *, enabled: bool) -> subprocess.CompletedProcess[str]:
    empty_path = tmp_path / "empty-path"
    empty_path.mkdir()
    environment = os.environ.copy()
    environment["PATH"] = str(empty_path)
    if enabled:
        environment["HOOK_RELEASE_GUARD"] = "1"
    else:
        environment.pop("HOOK_RELEASE_GUARD", None)
    return subprocess.run(
        ["/bin/bash", str(LAUNCHER), str(HOOK)],
        cwd=REPO_ROOT,
        env=environment,
        input=json.dumps(
            {"tool_name": "Bash", "tool_input": {"command": "git status"}}
        ),
        capture_output=True,
        text=True,
        check=False,
    )


def test_release_guard_launcher_is_noop_without_python_when_disabled(
    tmp_path: Path,
) -> None:
    result = _run_launcher(tmp_path, enabled=False)

    assert result.returncode == 0
    assert not result.stdout
    assert not result.stderr


def test_release_guard_launcher_fails_without_python_when_enabled(
    tmp_path: Path,
) -> None:
    result = _run_launcher(tmp_path, enabled=True)

    assert result.returncode == 127
    assert "python3" in result.stderr


def test_release_guard_hook_uses_closed_shell_launcher() -> None:
    config = json.loads(HOOK_CONFIG.read_text(encoding="utf-8"))

    assert config["failurePolicy"] == "closed"
    assert config["handler"]["program"] == "bash"
    assert config["handler"]["arguments"] == [
        {"packageFile": "hook.sh"},
        {"packageFile": "hook.py"},
    ]


@pytest.mark.parametrize(
    "command",
    [
        "gh release view v6.13.0 --repo alexei-led/cc-thingz",
        "gh release list --repo alexei-led/cc-thingz",
        "gh release create v6.13.0 --dry-run",
        "gh release create v6.13.0 --repo alexei-led/cc-thingz --dry-run",
    ],
)
def test_release_guard_allows_read_only_and_dry_run(command: str) -> None:
    result = _run_hook(command)

    assert result.returncode == 0
    assert not result.stdout


def test_release_guard_blocks_placeholder_notes(tmp_path: Path) -> None:
    notes = tmp_path / "notes.md"
    notes.write_text("## Changes\n\nTODO: add notes\n")

    result = _run_hook(_command(notes))

    assert result.returncode == 2
    assert "meaningful user-visible content" in result.stderr


def test_release_guard_allows_reviewed_notes_with_exact_identity(
    tmp_path: Path,
) -> None:
    notes = tmp_path / "notes.md"
    notes.write_text("Fix stale cache lookups.\n")

    result = _run_hook(_command(notes))

    assert result.returncode == 0
    assert not result.stderr


def test_release_guard_requires_verify_tag_and_exact_title(tmp_path: Path) -> None:
    notes = tmp_path / "notes.md"
    notes.write_text("Fix stale cache lookups.\n")
    command = (
        _command(notes)
        .replace("--verify-tag ", "")
        .replace("--title v6.13.0", "--title wrong")
    )

    result = _run_hook(command)

    assert result.returncode == 2
    assert "title must exactly match" in result.stderr


def test_release_guard_blocks_compound_and_unknown_mutations(tmp_path: Path) -> None:
    notes = tmp_path / "notes.md"
    notes.write_text("Fix stale cache lookups.\n")
    command = f"{_command(notes)} && echo done"

    compound = _run_hook(command)
    unknown = _run_hook("gh release delete v6.13.0 --repo alexei-led/cc-thingz")

    assert compound.returncode == 2
    assert "compound shell commands" in compound.stderr
    assert unknown.returncode == 2
    assert "unsupported GitHub release command" in unknown.stderr


def test_release_guard_uses_pi_pre_tool_envelope(tmp_path: Path) -> None:
    notes = tmp_path / "notes.md"
    notes.write_text("TODO\n")

    result = _run_hook(_command(notes), pi_runtime=True)

    assert result.returncode == 0
    assert json.loads(result.stdout) == {
        "decision": "deny",
        "reason": "release-guard: release notes need meaningful user-visible content",
    }
    assert not result.stderr
