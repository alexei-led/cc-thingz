"""Behavior tests for the compact specctl CLI."""

from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path

import pytest
from conftest import REPO_ROOT

SPECCTL = REPO_ROOT / "src" / "skills" / "spec-flow" / "scripts" / "specctl.py"
WRAPPER = REPO_ROOT / "src" / "skills" / "spec-flow" / "scripts" / "specctl"

_spec = importlib.util.spec_from_file_location("specctl_module", SPECCTL)
assert _spec is not None and _spec.loader is not None
specctl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(specctl)


def run_specctl(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["python3", str(SPECCTL), *args],
        capture_output=True,
        text=True,
        cwd=cwd,
        timeout=10,
    )


def parsed_meta(path: Path) -> dict:
    meta, _ = specctl.parse_frontmatter(path.read_text(encoding="utf-8"))
    return meta


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
# Frontmatter round-trip safety
# ---------------------------------------------------------------------------


def test_done_summary_with_hash_survives_reload_and_resave(empty_spec: Path):
    """A value containing " #" (e.g. an issue reference) must not be
    truncated by comment-stripping across repeated load-then-save cycles.

    Pre-fix, strip_comment() cut everything from " #" onward, so this
    assertion failed with the file containing only "Fixed auth bug"
    (parsed meta: {'done-summary': 'Fixed auth bug', ...}).
    """
    task = write_task(empty_spec, "TASK-hash")
    write_task(empty_spec, "TASK-other")
    assert run_specctl("start", "TASK-hash", cwd=empty_spec).returncode == 0

    summary = "Fixed auth bug #42: added regression test"
    done = run_specctl(
        "done",
        "TASK-hash",
        "--summary",
        summary,
        "--tests",
        "pytest passed",
        cwd=empty_spec,
    )
    assert done.returncode == 0
    assert summary in task.read_text(encoding="utf-8")
    assert parsed_meta(task)["done-summary"] == summary

    # A second load-then-save cycle (any of start/done/dep/reset) must not
    # truncate the value further.
    dep = run_specctl("dep", "add", "TASK-hash", "TASK-other", cwd=empty_spec)
    assert dep.returncode == 0
    assert summary in task.read_text(encoding="utf-8")
    assert parsed_meta(task)["done-summary"] == summary


def test_done_tests_with_leading_quote_survives_reload_and_resave(empty_spec: Path):
    task = write_task(empty_spec, "TASK-quote")
    write_task(empty_spec, "TASK-other")
    assert run_specctl("start", "TASK-quote", cwd=empty_spec).returncode == 0

    tests_note = '"already reviewed" via pytest'
    done = run_specctl(
        "done",
        "TASK-quote",
        "--summary",
        "Reviewed output",
        "--tests",
        tests_note,
        cwd=empty_spec,
    )
    assert done.returncode == 0
    assert parsed_meta(task)["done-tests"] == tests_note

    dep = run_specctl("dep", "add", "TASK-quote", "TASK-other", cwd=empty_spec)
    assert dep.returncode == 0
    assert parsed_meta(task)["done-tests"] == tests_note


def test_done_summary_ending_in_quote_survives_reload_and_resave(empty_spec: Path):
    """A value ending in an unmatched quote character must not be corrupted
    across repeated load-then-save cycles.

    Pre-fix, needs_quoting() only checked for a *leading* quote, so a value
    like 'Fixed the "bug"' was written unquoted; the unquoted parse path then
    blindly stripped the trailing quote with `.strip("\"'")`, corrupting the
    stored value to 'Fixed the "bug' on the very next load-then-save cycle.
    """
    task = write_task(empty_spec, "TASK-trailing-quote")
    write_task(empty_spec, "TASK-other")
    assert run_specctl("start", "TASK-trailing-quote", cwd=empty_spec).returncode == 0

    summary = 'Fixed the "bug"'
    done = run_specctl(
        "done",
        "TASK-trailing-quote",
        "--summary",
        summary,
        "--tests",
        "pytest passed",
        cwd=empty_spec,
    )
    assert done.returncode == 0
    assert parsed_meta(task)["done-summary"] == summary

    # A second load-then-save cycle must not corrupt the value further.
    dep = run_specctl("dep", "add", "TASK-trailing-quote", "TASK-other", cwd=empty_spec)
    assert dep.returncode == 0
    assert parsed_meta(task)["done-summary"] == summary


def test_done_summary_with_internal_quotes_survives_reload_and_resave(empty_spec: Path):
    """A value with internal quote characters that neither starts nor ends
    with a quote must round-trip unchanged."""
    task = write_task(empty_spec, "TASK-internal-quote")
    write_task(empty_spec, "TASK-other")
    assert run_specctl("start", "TASK-internal-quote", cwd=empty_spec).returncode == 0

    summary = 'He said "hello" to the reviewer'
    done = run_specctl(
        "done",
        "TASK-internal-quote",
        "--summary",
        summary,
        "--tests",
        "pytest passed",
        cwd=empty_spec,
    )
    assert done.returncode == 0
    assert parsed_meta(task)["done-summary"] == summary

    dep = run_specctl("dep", "add", "TASK-internal-quote", "TASK-other", cwd=empty_spec)
    assert dep.returncode == 0
    assert parsed_meta(task)["done-summary"] == summary


def test_list_item_with_hash_round_trips_through_dump_and_parse():
    """List items must be quoted the same way scalars are: a " #" inside a
    list item must not be truncated by comment-stripping on load.

    Pre-fix, dump_frontmatter()'s list branch never called quote_scalar(), so
    an item like "urgent #p1" was written unquoted and then truncated to
    "urgent" (comment-stripped) on the next parse.
    """
    meta = {"id": "TASK-x", "tags": ["urgent #p1", "other"]}
    text = specctl.dump_frontmatter(meta, "")
    reparsed, _ = specctl.parse_frontmatter(text)
    assert reparsed["tags"] == ["urgent #p1", "other"]

    # A second load-then-save cycle must not truncate the value further.
    text2 = specctl.dump_frontmatter(reparsed, "")
    reparsed2, _ = specctl.parse_frontmatter(text2)
    assert reparsed2["tags"] == ["urgent #p1", "other"]


# ---------------------------------------------------------------------------
# Atomic writes
# ---------------------------------------------------------------------------


def test_atomic_write_writes_target_with_no_temp_droppings(tmp_path: Path):
    target = tmp_path / "PROGRESS.md"

    specctl.atomic_write(target, "hello\n")

    assert target.read_text(encoding="utf-8") == "hello\n"
    assert list(tmp_path.iterdir()) == [target]


def test_atomic_write_leaves_original_untouched_when_replace_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    target = tmp_path / "PROGRESS.md"
    target.write_text("original\n", encoding="utf-8")

    def boom(*_args: object, **_kwargs: object) -> None:
        raise OSError("simulated replace failure")

    monkeypatch.setattr(specctl.os, "replace", boom)

    with pytest.raises(OSError):
        specctl.atomic_write(target, "new\n")

    assert target.read_text(encoding="utf-8") == "original\n"
    assert list(tmp_path.iterdir()) == [target]


def test_log_appends_without_rewriting_existing_lines(empty_spec: Path):
    progress = empty_spec / ".spec" / "PROGRESS.md"
    progress.write_text("09:00 INIT .spec/\n", encoding="utf-8")
    write_task(empty_spec, "TASK-a")

    result = run_specctl("start", "TASK-a", cwd=empty_spec)

    assert result.returncode == 0
    lines = progress.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "09:00 INIT .spec/"
    assert lines[-1].endswith("START TASK-a")


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
