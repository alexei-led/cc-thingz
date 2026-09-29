"""End-to-end: a squash-merged branch/worktree cleanup must clear git-
guardrails through the real rendered Claude adapter command, not just
through hook.sh directly."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest
from conftest import REPO_ROOT

PLUGIN_ROOT = REPO_ROOT / "dist/claude/git-flow"
HOOKS_JSON = PLUGIN_ROOT / "hooks/hooks.json"

ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@example.com",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@example.com",
    "CLAUDE_HOOK_CONFIG": "/nonexistent",
}


def _build() -> None:
    subprocess.run(["agbun", "build", "--root", str(REPO_ROOT)], check=True)


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, env=ENV, check=True, capture_output=True, text=True
    ).stdout.strip()


def commit(repo: Path, name: str, content: str) -> None:
    (repo / name).write_text(content)
    git(repo, "add", name)
    git(repo, "commit", "-q", "-m", name)


@pytest.fixture()
def clone(tmp_path: Path) -> Path:
    """A clone of origin/main with a squash-merged feature branch checked
    out in its own worktree, and a real unmerged branch besides it."""
    origin = tmp_path / "origin"
    seed = tmp_path / "seed"
    work = tmp_path / "work"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    git(tmp_path, "clone", "-q", str(origin), str(seed))
    commit(seed, "base.txt", "base\n")
    git(seed, "push", "-q", "origin", "HEAD:main")

    git(seed, "switch", "-q", "-c", "feature")
    commit(seed, "a.txt", "a1\n")
    commit(seed, "a.txt", "a2\n")
    git(seed, "push", "-q", "origin", "feature")
    git(seed, "switch", "-q", "-c", "unmerged", "main")
    commit(seed, "c.txt", "c\n")
    git(seed, "push", "-q", "origin", "unmerged")

    git(seed, "switch", "-q", "main")
    git(seed, "merge", "-q", "--squash", "feature")
    git(seed, "commit", "-q", "-m", "squash merge feature")
    git(seed, "push", "-q", "origin", "main")

    git(tmp_path, "clone", "-q", str(origin), str(work))
    git(work, "branch", "-q", "feature", "origin/feature")
    git(work, "branch", "-q", "unmerged", "origin/unmerged")
    return work


def add_worktree(clone: Path, name: str, branch: str) -> Path:
    path = clone.parent / f"wt-{name}"
    git(clone, "worktree", "add", "-q", str(path), branch)
    return path


def run_through_adapter(command: str, work: Path) -> subprocess.CompletedProcess[str]:
    payload = {
        "hook_event_name": "PreToolUse",
        "session_id": "e2e",
        "cwd": str(work),
        "tool_name": "Bash",
        "tool_input": {"command": command},
    }
    handler_command = json.loads(HOOKS_JSON.read_text())["hooks"]["PreToolUse"][0][
        "hooks"
    ][0]["command"]
    environment = {**ENV, "CLAUDE_PLUGIN_ROOT": str(PLUGIN_ROOT)}
    return subprocess.run(
        ["bash", "-c", handler_command],
        cwd=work,
        env=environment,
        input=json.dumps(payload),
        capture_output=True,
        text=True,
    )


def test_merged_worktree_and_branch_cleanup_is_allowed(clone: Path) -> None:
    _build()
    path = add_worktree(clone, "merged", "feature")
    command = (
        f"cd {clone} && git worktree remove --force {path} && git branch -D feature"
    )
    result = run_through_adapter(command, clone.parent)
    assert result.returncode == 0, result.stdout + result.stderr
    assert '"deny"' not in result.stdout


def test_unmerged_branch_cleanup_is_blocked(clone: Path) -> None:
    _build()
    command = f"cd {clone} && git branch -D unmerged"
    result = run_through_adapter(command, clone.parent)
    assert result.returncode == 0
    assert '"permissionDecision":"deny"' in result.stdout
