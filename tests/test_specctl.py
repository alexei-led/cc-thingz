"""Behavior tests for the compact specctl CLI."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from conftest import REPO_ROOT

SPECCTL = REPO_ROOT / "src" / "skills" / "spec-flow" / "scripts" / "specctl.py"
WRAPPER = REPO_ROOT / "src" / "skills" / "spec-flow" / "scripts" / "specctl"


def run_specctl(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["python3", str(SPECCTL), *args],
        capture_output=True,
        text=True,
        cwd=cwd,
        timeout=10,
    )


@pytest.fixture()
def empty_spec(tmp_path: Path) -> Path:
    for subdir in ("tasks", "reqs", "epics", "memory"):
        (tmp_path / ".spec" / subdir).mkdir(parents=True)
    return tmp_path


def write_task(
    root: Path,
    task_id: str,
    *,
    status: str = "todo",
    epic: str | None = None,
    blocked_by: list[str] | None = None,
    subdir: str | None = None,
    meaningful: bool = True,
) -> Path:
    task_dir = root / ".spec" / "tasks"
    if subdir:
        task_dir /= subdir
    task_dir.mkdir(parents=True, exist_ok=True)
    lines = ["---", f"id: {task_id}", f"status: {status}", "priority: normal"]
    if epic:
        lines.append(f"epic: {epic}")
    if blocked_by is not None:
        lines.append(f"blocked-by: [{', '.join(blocked_by)}]")
    description = "Add CSV export for selected records." if meaningful else "TBD"
    acceptance = "CSV export command writes selected records." if meaningful else "TBD"
    acceptance_lines = [f"- [ ] {acceptance}"]
    if meaningful:
        acceptance_lines.append("- [ ] `pytest tests/test_export.py` passes.")
    lines.extend(
        [
            "---",
            f"# {task_id}",
            "",
            "## Description",
            "",
            description,
            "",
            "## Acceptance",
            "",
            *acceptance_lines,
            "",
            "## Files",
            "",
            "- `src/export.py` — export behavior",
        ]
    )
    path = task_dir / f"{task_id}.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Entrypoints and empty state
# ---------------------------------------------------------------------------


def test_help_exits_zero():
    result = run_specctl("--help")
    assert result.returncode == 0
    assert "specctl" in result.stdout.lower()


@pytest.mark.parametrize("cmd", ["status", "ready", "new", "checkpoint", "session"])
def test_subcommand_help_exits_zero(cmd: str):
    result = run_specctl(cmd, "--help")
    assert result.returncode == 0


def test_wrapper_entrypoint_executes():
    result = subprocess.run(
        [str(WRAPPER), "--help"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert "specctl" in result.stdout.lower()


@pytest.mark.parametrize("cmd", ["status", "ready", "validate"])
def test_read_commands_fail_without_spec(cmd: str, tmp_path: Path):
    result = run_specctl(cmd, cwd=tmp_path)
    assert result.returncode != 0
    assert ".spec/ not found" in result.stderr


def test_init_creates_spec_tree(tmp_path: Path):
    result = run_specctl("init", cwd=tmp_path)
    assert result.returncode == 0
    for subdir in ("tasks", "reqs", "epics", "memory"):
        assert (tmp_path / ".spec" / subdir).is_dir()


# ---------------------------------------------------------------------------
# Discovery, readiness, validation quality
# ---------------------------------------------------------------------------


def test_status_and_ready_json(empty_spec: Path):
    write_task(empty_spec, "TASK-export")
    status = run_specctl("status", "--json", cwd=empty_spec)
    ready = run_specctl("ready", "--json", cwd=empty_spec)
    assert status.returncode == 0
    assert ready.returncode == 0
    assert json.loads(status.stdout)["total"] == 1
    assert json.loads(ready.stdout)[0]["id"] == "TASK-export"


def test_nested_tasks_are_discovered(empty_spec: Path):
    write_task(empty_spec, "TASK-nested", subdir="exports")
    result = run_specctl("ready", "--json", cwd=empty_spec)
    assert result.returncode == 0
    assert json.loads(result.stdout)[0]["id"] == "TASK-nested"


def test_ready_epic_filter_respects_cross_epic_done_dependency(empty_spec: Path):
    write_task(empty_spec, "TASK-a", status="done", epic="EPIC-one")
    write_task(empty_spec, "TASK-b", epic="EPIC-two", blocked_by=["TASK-a"])
    result = run_specctl("ready", "--epic", "EPIC-two", "--json", cwd=empty_spec)
    assert result.returncode == 0
    assert [item["id"] for item in json.loads(result.stdout)] == ["TASK-b"]


def test_validate_rejects_placeholder_task(empty_spec: Path):
    write_task(empty_spec, "TASK-vague", meaningful=False)
    result = run_specctl("validate", cwd=empty_spec)
    assert result.returncode != 0
    assert "missing meaningful Description" in result.stdout
    assert "missing meaningful Acceptance" in result.stdout


def test_new_task_is_intentionally_draft_until_refined(tmp_path: Path):
    created = run_specctl("new", "task", "exports/csv", cwd=tmp_path)
    assert created.returncode == 0
    task_path = tmp_path / ".spec" / "tasks" / "exports" / "TASK-csv.md"
    assert task_path.exists()
    validation = run_specctl("validate", cwd=tmp_path)
    assert validation.returncode != 0
    assert "TASK-csv: missing meaningful Description" in validation.stdout
    assert "TASK-csv: missing meaningful Acceptance" in validation.stdout
    assert "TASK-csv: missing meaningful Files" in validation.stdout


# ---------------------------------------------------------------------------
# Sessions and closeout
# ---------------------------------------------------------------------------


def test_start_refuses_to_overwrite_other_active_session(empty_spec: Path):
    task_a = write_task(empty_spec, "TASK-a")
    task_b = write_task(empty_spec, "TASK-b")
    assert run_specctl("start", "TASK-a", cwd=empty_spec).returncode == 0

    result = run_specctl("start", "TASK-b", cwd=empty_spec)

    assert result.returncode != 0
    assert "Session exists for TASK-a" in result.stderr
    assert "status: in-progress" in task_a.read_text(encoding="utf-8")
    assert "status: todo" in task_b.read_text(encoding="utf-8")


def test_done_requires_evidence_and_clears_matching_session(empty_spec: Path):
    task = write_task(empty_spec, "TASK-close")
    assert run_specctl("start", "TASK-close", cwd=empty_spec).returncode == 0

    missing = run_specctl("done", "TASK-close", cwd=empty_spec)
    assert missing.returncode != 0
    assert "Missing completion evidence" in missing.stderr

    done = run_specctl(
        "done",
        "TASK-close",
        "--summary",
        "Implemented close path",
        "--tests",
        "pytest passed",
        cwd=empty_spec,
    )
    assert done.returncode == 0
    assert "status: done" in task.read_text(encoding="utf-8")
    session = run_specctl("session", "show", cwd=empty_spec)
    assert "No active session" in session.stdout


def test_done_refuses_to_clear_another_task_session(empty_spec: Path):
    task_b = write_task(empty_spec, "TASK-b")
    write_task(empty_spec, "TASK-a")
    assert run_specctl("start", "TASK-a", cwd=empty_spec).returncode == 0

    result = run_specctl(
        "done",
        "TASK-b",
        "--summary",
        "Finished elsewhere",
        "--tests",
        "manual check passed",
        cwd=empty_spec,
    )

    assert result.returncode != 0
    assert "Active session is for TASK-a" in result.stderr
    assert "status: todo" in task_b.read_text(encoding="utf-8")


def test_reset_clears_active_session(empty_spec: Path):
    task = write_task(empty_spec, "TASK-reset")
    assert run_specctl("start", "TASK-reset", cwd=empty_spec).returncode == 0

    result = run_specctl("reset", "TASK-reset", cwd=empty_spec)

    assert result.returncode == 0
    assert "status: todo" in task.read_text(encoding="utf-8")
    session = run_specctl("session", "show", cwd=empty_spec)
    assert "No active session" in session.stdout


def test_handoff_reports_uncommitted_changes(tmp_path: Path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True
    )
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    for subdir in ("tasks", "reqs", "epics", "memory"):
        (tmp_path / ".spec" / subdir).mkdir(parents=True)
    write_task(tmp_path, "TASK-work")
    (tmp_path / "app.txt").write_text("initial\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=tmp_path, check=True)
    assert run_specctl("start", "TASK-work", cwd=tmp_path).returncode == 0
    (tmp_path / "app.txt").write_text("changed\n", encoding="utf-8")

    result = run_specctl("session", "handoff", cwd=tmp_path)

    assert result.returncode == 0
    assert "app.txt" in result.stdout
    assert "Changes: none" not in result.stdout


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------


def test_dep_add_and_remove(empty_spec: Path):
    task_b = write_task(empty_spec, "TASK-b")
    write_task(empty_spec, "TASK-a")

    added = run_specctl("dep", "add", "TASK-b", "TASK-a", cwd=empty_spec)
    assert added.returncode == 0
    assert "blocked-by:\n  - TASK-a" in task_b.read_text(encoding="utf-8")

    removed = run_specctl("dep", "rm", "TASK-b", "TASK-a", cwd=empty_spec)
    assert removed.returncode == 0
    assert "blocked-by: []" in task_b.read_text(encoding="utf-8")


def test_dep_add_refuses_cycles(empty_spec: Path):
    write_task(empty_spec, "TASK-a", blocked_by=["TASK-b"])
    write_task(empty_spec, "TASK-b")

    result = run_specctl("dep", "add", "TASK-b", "TASK-a", cwd=empty_spec)

    assert result.returncode != 0
    assert "creates a cycle" in result.stderr
