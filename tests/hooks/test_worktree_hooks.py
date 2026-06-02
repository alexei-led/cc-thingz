"""Tests for safe worktree create/remove hooks."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CREATE_HOOK = ROOT / "src" / "hooks" / "worktree-create" / "hook.sh"
REMOVE_HOOK = ROOT / "src" / "hooks" / "worktree-remove" / "hook.sh"
SETUP_SCRIPT = (
    ROOT / "src" / "skills" / "using-git-worktrees" / "scripts" / "setup-worktree.sh"
)


@pytest.fixture(autouse=True)
def require_jq() -> None:
    if shutil.which("jq") is None:
        pytest.skip("jq is required by worktree hooks")


def run_hook(hook: Path, payload: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(hook)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=False,
    )


def run_setup(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SETUP_SCRIPT), *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
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
        check=check,
    )


def init_repo(path: Path) -> Path:
    path.mkdir()
    git(path, "init", "-b", "main")
    (path / "README.md").write_text("hello\n")
    git(path, "add", "README.md")
    git(path, "commit", "-m", "init")
    return path.resolve()


def create_worktree(repo: Path, branch: str) -> Path:
    result = run_hook(CREATE_HOOK, {"name": branch, "cwd": str(repo)})
    assert result.returncode == 0, result.stderr
    path = Path(result.stdout.strip())
    assert path.is_dir()
    return path


def test_create_uses_managed_root_with_space_in_repo_path(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo with spaces")

    worktree = create_worktree(repo, "feature/test")

    assert worktree == repo.with_name(f"{repo.name}.worktrees") / "feature-test"


def test_setup_script_uses_managed_root_and_refuses_auto_setup(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo with spaces")

    result = run_setup(repo, "feature/test")

    assert result.returncode == 0, result.stderr + result.stdout
    worktree = repo.with_name(f"{repo.name}.worktrees") / "feature-test"
    assert worktree.is_dir()
    assert "WORKTREE READY" in result.stdout


def test_setup_script_refuses_dirty_current_worktree(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    (repo / "dirty.txt").write_text("dirty\n")

    result = run_setup(repo, "feature/test")

    assert result.returncode == 1
    assert "current worktree is dirty" in result.stderr


def test_setup_script_checks_out_existing_local_branch(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    git(repo, "branch", "feature/existing")

    result = run_setup(repo, "feature/existing")

    assert result.returncode == 0, result.stderr + result.stdout
    worktree = repo.with_name(f"{repo.name}.worktrees") / "feature-existing"
    assert worktree.is_dir()
    assert (
        git(worktree, "branch", "--show-current").stdout.strip() == "feature/existing"
    )


def test_create_refuses_dirty_current_worktree(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    (repo / "dirty.txt").write_text("dirty\n")

    result = run_hook(CREATE_HOOK, {"name": "feature/test", "cwd": str(repo)})

    assert result.returncode == 1
    assert "current worktree is dirty" in result.stderr


def test_create_branch_detection_is_exact(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    checked_out = create_worktree(repo, "feature/test-other")

    worktree = create_worktree(repo, "feature/test")

    assert checked_out.name == "feature-test-other"
    assert worktree.name == "feature-test"


def test_remove_refuses_unmanaged_worktree(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    unmanaged = tmp_path / "repo-feature-test"
    git(repo, "worktree", "add", str(unmanaged), "-b", "feature/test")

    result = run_hook(REMOVE_HOOK, {"worktree_path": str(unmanaged)})

    assert result.returncode == 1
    assert "unmanaged worktree path" in result.stderr
    assert unmanaged.is_dir()


def test_remove_refuses_dirty_managed_worktree(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    worktree = create_worktree(repo, "feature/test")
    (worktree / "dirty.txt").write_text("dirty\n")

    result = run_hook(REMOVE_HOOK, {"worktree_path": str(worktree)})

    assert result.returncode == 1
    assert "dirty worktree" in result.stderr
    assert worktree.is_dir()


def test_remove_keeps_unmerged_branch_after_removing_clean_worktree(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    worktree = create_worktree(repo, "feature/test")
    (worktree / "feature.txt").write_text("feature\n")
    git(worktree, "add", "feature.txt")
    git(worktree, "commit", "-m", "feature")

    result = run_hook(REMOVE_HOOK, {"worktree_path": str(worktree)})

    assert result.returncode == 0, result.stderr
    assert not worktree.exists()
    branches = git(repo, "branch", "--list", "feature/test").stdout
    assert "feature/test" in branches
    assert "not fully merged" in result.stderr
