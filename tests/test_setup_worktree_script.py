from __future__ import annotations

import json
import os
import stat
import subprocess
from pathlib import Path

import pytest
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


@pytest.mark.parametrize(
    ("manager", "lockfile", "version", "expected"),
    [
        ("npm", "package-lock.json", "10.0.0", "ci"),
        ("pnpm", "pnpm-lock.yaml", "10.0.0", "install --frozen-lockfile"),
        ("bun", "bun.lock", "1.2.0", "install --frozen-lockfile"),
        ("yarn", "yarn.lock", "1.22.0", "install --frozen-lockfile"),
        ("yarn", "yarn.lock", "4.0.0", "install --immutable"),
    ],
)
def test_setup_uses_frozen_project_manager(
    tmp_path: Path, manager: str, lockfile: str, version: str, expected: str
) -> None:
    repo = init_repo(tmp_path, "main")
    write_commit(
        repo,
        "package.json",
        json.dumps({"packageManager": f"{manager}@{version}"}),
        "package",
    )
    write_commit(repo, lockfile, "locked\n", "lock")
    env = make_exit_stub(tmp_path, manager, 0)
    binary = tmp_path / "bin" / manager
    binary.write_text(
        f'#!/bin/sh\nif [ "$1" = --version ]; then echo {version}; '
        'else echo "MANAGER $*"; fi\n'
    )

    result = run([str(SCRIPT), "--setup", "feature"], repo, env=env)

    assert result.returncode == 0, result.stdout
    assert f"MANAGER {expected}" in result.stdout
    worktree = tmp_path / "repo-main.worktrees" / "feature"
    assert (worktree / lockfile).read_text() == "locked\n"


def test_setup_refuses_conflicting_manager_without_removing_worktree(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path, "main")
    write_commit(repo, "package.json", '{"packageManager":"pnpm@10.0.0"}', "package")
    write_commit(repo, "package-lock.json", "locked\n", "lock")

    result = run([str(SCRIPT), "--setup", "feature"], repo)

    assert result.returncode == 1
    assert "packageManager conflicts" in result.stdout
    assert (
        tmp_path / "repo-main.worktrees" / "feature" / "file.txt"
    ).read_text() == "base\n"


def test_reports_base_divergence_without_resetting_or_fetching(tmp_path: Path) -> None:
    repo = init_repo(tmp_path, "main")
    git(repo, "branch", "tracking")
    git(repo, "branch", "--set-upstream-to=tracking", "main")
    write_commit(repo, "ahead.txt", "ahead\n", "ahead")
    original = git(repo, "rev-parse", "HEAD")

    result = run([str(SCRIPT), "feature"], repo)

    assert result.returncode == 0
    assert "ahead 1, behind 0" in result.stdout
    assert git(repo, "rev-parse", "main") == original


def test_python_setup_and_tests_use_uv(tmp_path: Path) -> None:
    repo = init_repo(tmp_path, "main")
    write_commit(repo, "pyproject.toml", '[project]\nname="fixture"\n', "python")
    env = make_exit_stub(tmp_path, "uv", 0)
    (tmp_path / "bin" / "uv").write_text('#!/bin/sh\necho "UV $*"\n')

    result = run([str(SCRIPT), "--setup", "--test", "feature"], repo, env=env)

    assert result.returncode == 0
    assert "UV sync --locked" in result.stdout
    assert "UV run --locked --extra test python -m pytest" in result.stdout


def test_setup_refuses_missing_lock_without_running_installer(tmp_path: Path) -> None:
    repo = init_repo(tmp_path, "main")
    write_commit(repo, "package.json", '{"packageManager":"npm@10.0.0"}', "package")
    result = run([str(SCRIPT), "--setup", "feature"], repo)
    assert result.returncode == 1
    assert "frozen setup requires a committed lockfile" in result.stdout
    assert not (tmp_path / "repo-main.worktrees/feature/package-lock.json").exists()


def test_requirements_setup_uses_worktree_virtualenv(tmp_path: Path) -> None:
    repo = init_repo(tmp_path, "main")
    write_commit(repo, "requirements.txt", "pytest==8.0.0\n", "requirements")
    env = make_exit_stub(tmp_path, "uv", 0)
    (tmp_path / "bin" / "uv").write_text('#!/bin/sh\necho "UV $*"\n')
    result = run([str(SCRIPT), "--setup", "feature"], repo, env=env)
    assert result.returncode == 0
    assert "UV venv" in result.stdout
    assert "UV pip sync --python .venv/bin/python requirements.txt" in result.stdout
