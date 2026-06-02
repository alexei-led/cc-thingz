from __future__ import annotations

import subprocess
from pathlib import Path


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=True)


def test_commit_state_gather_reports_suspicious_paths(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    run(["git", "init"], repo)
    run(["git", "config", "user.name", "Test User"], repo)
    run(["git", "config", "user.email", "test@example.com"], repo)

    (repo / "app.ts").write_text("console.log('v1')\n")
    run(["git", "add", "app.ts"], repo)
    run(["git", "commit", "-m", "feat: init"], repo)

    (repo / "app.ts").write_text("console.log('v2')\n")
    (repo / ".env").write_text("TOKEN=secret\n")

    script = Path("src/skills/committing-code/scripts/commit-state.sh").resolve()
    out = run([str(script), "gather"], repo).stdout

    assert "REPO_STATE\nclean" in out
    assert "CHANGED_PATHS" in out
    assert "app.ts" in out
    assert ".env" in out
    assert "SUSPICIOUS_PATH_COUNT\n1" in out
    assert "SUSPICIOUS_PATHS\n.env" in out


def test_commit_state_gather_reports_suspicious_content_without_value(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    run(["git", "init"], repo)
    run(["git", "config", "user.name", "Test User"], repo)
    run(["git", "config", "user.email", "test@example.com"], repo)

    (repo / "app.ts").write_text("console.log('v1')\n")
    run(["git", "add", "app.ts"], repo)
    run(["git", "commit", "-m", "feat: init"], repo)

    (repo / "app.ts").write_text("const api_key = 'secret-value'\n")

    script = Path("src/skills/committing-code/scripts/commit-state.sh").resolve()
    out = run([str(script), "gather"], repo).stdout

    assert "SUSPICIOUS_PATHS\napp.ts" in out
    assert "secret-value" not in out


def test_commit_state_paths_includes_untracked_files(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    run(["git", "init"], repo)
    run(["git", "config", "user.name", "Test User"], repo)
    run(["git", "config", "user.email", "test@example.com"], repo)

    (repo / "tracked.txt").write_text("a\n")
    run(["git", "add", "tracked.txt"], repo)
    run(["git", "commit", "-m", "chore: init"], repo)

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
