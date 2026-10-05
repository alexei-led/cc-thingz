from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=True)


@pytest.fixture(scope="module")
def committed_seed(tmp_path_factory: pytest.TempPathFactory) -> Path:
    repo = tmp_path_factory.mktemp("commit-state")
    run(["git", "init"], repo)
    run(["git", "config", "user.name", "Test User"], repo)
    run(["git", "config", "user.email", "test@example.com"], repo)
    for name in ("app.ts", "tracked.txt"):
        (repo / name).write_text("initial\n")
    run(["git", "add", "."], repo)
    run(["git", "-c", "commit.gpgsign=false", "commit", "-m", "feat: init"], repo)
    return repo


@pytest.fixture
def repo(committed_seed: Path, tmp_path: Path) -> Path:
    return Path(shutil.copytree(committed_seed, tmp_path / "repo"))


@pytest.mark.parametrize(
    ("filename", "content", "secret"),
    [
        pytest.param(".env", "TOKEN=secret\n", "TOKEN=secret", id="secret-path"),
        pytest.param(
            "app.ts",
            "const api_key = 'secret-value'\n",
            "secret-value",
            id="secret-content",
        ),
    ],
)
def test_gather_reports_suspicious_paths_without_values(
    repo: Path, filename: str, content: str, secret: str
) -> None:
    (repo / filename).write_text(content)
    script = Path("src/skills/committing-code/scripts/commit-state.sh").resolve()
    out = run([str(script), "gather"], repo).stdout

    assert "REPO_STATE\nclean" in out
    assert "CHANGED_PATHS" in out
    assert "SUSPICIOUS_PATH_COUNT\n1" in out
    assert f"SUSPICIOUS_PATHS\n{filename}" in out
    assert secret not in out


def test_commit_state_paths_includes_untracked_files(repo: Path) -> None:

    (repo / "tracked.txt").write_text("b\n")
    (repo / "new.txt").write_text("c\n")

    script = Path("src/skills/committing-code/scripts/commit-state.sh").resolve()
    out = run([str(script), "paths"], repo).stdout.splitlines()

    assert out == ["new.txt", "tracked.txt"]


def test_commit_state_handles_unborn_branch(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    run(["git", "init"], repo)
    (repo / "new.txt").write_text("new\n")

    script = Path("src/skills/committing-code/scripts/commit-state.sh").resolve()
    result = run([str(script), "gather"], repo)

    assert "REPO_STATE\nclean" in result.stdout
    assert "new.txt" in result.stdout
