from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

from conftest import REPO_ROOT

SCRIPT = (
    REPO_ROOT
    / "src"
    / "skills"
    / "using-git-worktrees"
    / "scripts"
    / "setup-worktree.sh"
)


def run(
    args: list[str],
    cwd: Path,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(
        args,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        env=merged_env,
    )


def git(repo: Path, *args: str, env: dict[str, str] | None = None) -> str:
    result = run(["git", *args], repo, env=env)
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


def make_exit_stub(tmp_path: Path, name: str, exit_code: int) -> dict[str, str]:
    """Fake `name` binary on PATH that always exits with `exit_code`."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    script = bin_dir / name
    script.write_text(f"#!/bin/sh\nexit {exit_code}\n")
    script.chmod(script.stat().st_mode | stat.S_IXUSR)
    return {"PATH": f"{bin_dir}:{os.environ['PATH']}"}


def test_failing_baseline_tests_still_prints_ready_and_exits_zero(
    tmp_path: Path,
) -> None:
    """Pin: a failing baseline test command must not swallow the
    WORKTREE READY summary — pre-fix, `set -euo pipefail` aborted the script
    before the summary printed, hiding the worktree path."""
    repo = init_repo(tmp_path, "main")
    write_commit(repo, "Makefile", "test:\n\t@exit 1\n", "add failing test target")

    result = run([str(SCRIPT), "--test", "feature"], repo)

    assert result.returncode == 0, result.stdout
    assert "warning: baseline tests failed" in result.stdout
    assert "WORKTREE READY" in result.stdout
    assert "Branch: feature" in result.stdout


def test_failing_dependency_setup_still_prints_ready_but_exits_nonzero(
    tmp_path: Path,
) -> None:
    """A failed dependency setup still leaves a usable worktree behind, so
    the summary (with its path) must print; the setup step is what actually
    failed though, so the script reports that via a non-zero exit."""
    repo = init_repo(tmp_path, "main")
    write_commit(repo, "Cargo.toml", '[package]\nname = "x"\n', "add cargo project")
    env = make_exit_stub(tmp_path, "cargo", 1)

    result = run([str(SCRIPT), "--setup", "feature"], repo, env=env)

    assert result.returncode == 1, result.stdout
    assert "warning: dependency setup failed" in result.stdout
    assert "WORKTREE READY" in result.stdout
    assert "Branch: feature" in result.stdout


def test_successful_setup_and_tests_print_ready_and_exit_zero(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path, "main")
    write_commit(repo, "Makefile", "test:\n\t@true\n", "add passing test target")

    result = run([str(SCRIPT), "--test", "feature"], repo)

    assert result.returncode == 0, result.stdout
    assert "warning: baseline tests failed" not in result.stdout
    assert "WORKTREE READY" in result.stdout
