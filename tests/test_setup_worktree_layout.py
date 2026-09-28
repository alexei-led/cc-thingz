"""Tests for setup-worktree.sh managed-root layout and safety checks."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from conftest import REPO_ROOT

SETUP_SCRIPT = (
    REPO_ROOT
    / "src"
    / "skills"
    / "using-git-worktrees"
    / "scripts"
    / "setup-worktree.sh"
)


def run_setup(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SETUP_SCRIPT), *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )


def git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update({"GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "test@example.com"})
    env.update(
        {"GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "test@example.com"}
    )
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )


def init_repo(path: Path) -> Path:
    path.mkdir()
    git(path, "init", "-b", "main")
    (path / "README.md").write_text("hello\n")
    git(path, "add", "README.md")
    git(path, "commit", "-m", "init")
    return path.resolve()


def test_uses_managed_root_with_space_in_repo_path(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo with spaces")

    result = run_setup(repo, "feature/test")

    assert result.returncode == 0, result.stderr + result.stdout
    worktree = repo.with_name(f"{repo.name}.worktrees") / "feature-test"
    assert worktree.is_dir()
    assert "WORKTREE READY" in result.stdout


def test_refuses_dirty_current_worktree(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    (repo / "dirty.txt").write_text("dirty\n")

    result = run_setup(repo, "feature/test")

    assert result.returncode == 1
    assert "current worktree is dirty" in result.stderr


def test_checks_out_existing_local_branch(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    git(repo, "branch", "feature/existing")

    result = run_setup(repo, "feature/existing")

    assert result.returncode == 0, result.stderr + result.stdout
    worktree = repo.with_name(f"{repo.name}.worktrees") / "feature-existing"
    assert worktree.is_dir()
    assert (
        git(worktree, "branch", "--show-current").stdout.strip() == "feature/existing"
    )
