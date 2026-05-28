from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from conftest import REPO_ROOT

SCRIPT = REPO_ROOT / "src" / "skills" / "cleanup-git" / "scripts" / "cleanup-git.sh"


def run(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def git(repo: Path, *args: str) -> str:
    result = run(["git", *args], repo)
    assert result.returncode == 0, result.stdout
    return result.stdout


def write_commit(repo: Path, filename: str, content: str, message: str) -> None:
    (repo / filename).write_text(content)
    git(repo, "add", filename)
    git(repo, "commit", "-m", message)


def init_repo(tmp_path: Path, base: str) -> Path:
    repo = tmp_path / f"repo-{base}"
    result = run(["git", "init", "-b", base, str(repo)], tmp_path)
    assert result.returncode == 0, result.stdout
    git(repo, "config", "user.email", "test@example.com")
    git(repo, "config", "user.name", "Test User")
    write_commit(repo, "file.txt", "base\n", "base")
    return repo


def add_merged_branch(repo: Path, base: str, branch: str = "cleanup-me") -> None:
    git(repo, "checkout", "-b", branch)
    write_commit(repo, f"{branch}.txt", "work\n", branch)
    git(repo, "checkout", base)
    git(repo, "merge", "--no-ff", branch, "-m", f"merge {branch}")


@pytest.mark.parametrize("base", ["main", "master", "trunk"])
def test_detects_mainstream_base_branches(tmp_path: Path, base: str) -> None:
    repo = init_repo(tmp_path, base)
    add_merged_branch(repo, base)

    result = run([str(SCRIPT)], repo)

    assert result.returncode == 0, result.stdout
    assert f"base branch: {base}" in result.stdout
    assert "delete cleanup-me (merged)" in result.stdout
    assert "would: git branch -d cleanup-me" in result.stdout
    assert f"delete {base}" not in result.stdout


def test_apply_deletes_merged_branch(tmp_path: Path) -> None:
    repo = init_repo(tmp_path, "master")
    add_merged_branch(repo, "master")

    result = run([str(SCRIPT), "--apply"], repo)

    assert result.returncode == 0, result.stdout
    assert "Deleted branch cleanup-me" in result.stdout
    branches = git(repo, "branch", "--format=%(refname:short)").splitlines()
    assert branches == ["master"]


def test_remote_default_branch_wins_over_local_fallback_order(tmp_path: Path) -> None:
    repo = init_repo(tmp_path, "main")
    git(repo, "branch", "master")
    origin = tmp_path / "origin.git"
    result = run(["git", "clone", "--bare", str(repo), str(origin)], tmp_path)
    assert result.returncode == 0, result.stdout
    result = run(
        ["git", "--git-dir", str(origin), "symbolic-ref", "HEAD", "refs/heads/master"],
        tmp_path,
    )
    assert result.returncode == 0, result.stdout
    git(repo, "remote", "add", "origin", str(origin))
    git(repo, "fetch", "origin")
    git(repo, "remote", "set-head", "origin", "-a")

    result = run([str(SCRIPT)], repo)

    assert result.returncode == 0, result.stdout
    assert "base branch: master" in result.stdout
