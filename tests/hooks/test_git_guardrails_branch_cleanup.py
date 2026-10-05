"""git-guardrails lets agents delete merged branches, including squash merges."""

import json
import os
import subprocess
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[2] / "src/hooks/git-guardrails/hook.sh"
DECIDE = Path(__file__).resolve().parents[2] / "src/hooks/git-guardrails/decide.py"
ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@example.com",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@example.com",
    "CLAUDE_HOOK_CONFIG": "/nonexistent",
}


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, env=ENV, check=True, capture_output=True, text=True
    ).stdout.strip()


def commit(repo: Path, name: str, content: str) -> None:
    (repo / name).write_text(content)
    git(repo, "add", name)
    git(repo, "commit", "-q", "-m", name)


@pytest.fixture(scope="module")
def clone(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A clone of origin/main with branches in each merge state."""
    tmp_path = tmp_path_factory.mktemp("guardrails")
    origin = tmp_path / "origin"
    seed = tmp_path / "seed"
    work = tmp_path / "work"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    git(tmp_path, "clone", "-q", str(origin), str(seed))
    commit(seed, "base.txt", "base\n")
    git(seed, "push", "-q", "origin", "HEAD:main")

    git(seed, "switch", "-q", "-c", "squashed")
    commit(seed, "a.txt", "a1\n")
    commit(seed, "a.txt", "a2\n")
    git(seed, "push", "-q", "origin", "squashed")
    git(seed, "switch", "-q", "-c", "fast-forwarded", "main")
    commit(seed, "b.txt", "b\n")
    git(seed, "push", "-q", "origin", "fast-forwarded")
    git(seed, "switch", "-q", "-c", "unmerged", "main")
    commit(seed, "c.txt", "c\n")
    git(seed, "push", "-q", "origin", "unmerged")

    git(seed, "switch", "-q", "main")
    git(seed, "merge", "-q", "--ff-only", "fast-forwarded")
    git(seed, "merge", "-q", "--squash", "squashed")
    git(seed, "commit", "-q", "-m", "squash merge")
    commit(seed, "later.txt", "master moved on\n")
    git(seed, "push", "-q", "origin", "main")

    git(tmp_path, "clone", "-q", str(origin), str(work))
    for branch in ("squashed", "fast-forwarded", "unmerged"):
        git(work, "branch", "-q", branch, f"origin/{branch}")
    return work


def run_hook(command: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    payload = json.dumps({"tool_input": {"command": command}, "cwd": str(cwd)})
    return subprocess.run(
        ["bash", str(HOOK), str(DECIDE)],
        input=payload,
        env=ENV,
        capture_output=True,
        text=True,
    )


@pytest.mark.parametrize(
    ("command", "allowed"),
    [
        ("git branch -D squashed", True),
        ("git branch -D fast-forwarded", True),
        ("git branch -D squashed fast-forwarded", True),
        ("git -C {work} branch -D squashed", True),
        ("git -C {parent} -C work branch -D squashed", True),
        ("git -C {parent} -C decoy branch -D squashed", False),
        ("git fetch origin && git branch -D squashed", True),
        ("git branch -D unmerged", False),
        ("git branch -D squashed unmerged", False),
        ("git branch -D missing", False),
        ("git branch -D main", False),
        ("cd /tmp && git branch -D squashed", False),
        ("cd {work} && git branch -D squashed", True),
        ("cd {parent} && cd work && git branch -D squashed", True),
        ("cd {work} && git branch -D unmerged", False),
        ("cd && git branch -D squashed", False),
        ("git --git-dir=/tmp/x.git branch -D squashed", False),
        ("git branch -D squashed && git reset --hard", False),
        ("git branch -D squashed; sudo git branch -D unmerged", False),
        ("git branch -D squashed; xargs git branch -D < names", False),
    ],
)
def test_branch_force_delete(clone: Path, command: str, allowed: bool) -> None:
    result = run_hook(command.format(work=clone, parent=clone.parent), clone)
    assert (result.returncode == 0) is allowed, result.stderr


def test_branch_checked_out_in_worktree_is_blocked(clone: Path) -> None:
    git(clone, "branch", "-q", "squashed-in-use", "squashed")
    git(clone, "worktree", "add", "-q", str(clone.parent / "wt"), "squashed-in-use")
    assert run_hook("git branch -D squashed-in-use", clone).returncode == 2


def add_worktree(clone: Path, name: str, start: str) -> Path:
    path = clone.parent / f"wt-{name}"
    git(clone, "worktree", "add", "-q", "-b", name, str(path), start)
    return path


@pytest.mark.parametrize(
    ("start", "dirty_tracked", "untracked", "allowed"),
    [
        ("origin/squashed", False, False, True),
        ("origin/fast-forwarded", False, True, False),
        ("origin/squashed", True, False, False),
        ("origin/unmerged", False, False, False),
    ],
)
def test_worktree_force_remove(
    clone: Path, start: str, dirty_tracked: bool, untracked: bool, allowed: bool
) -> None:
    name = f"wt{abs(hash((start, dirty_tracked, untracked)))}"
    path = add_worktree(clone, name, start)
    if dirty_tracked:
        (path / "base.txt").write_text("edited\n")
    if untracked:
        (path / "scratch.log").write_text("junk\n")
    result = run_hook(f"git worktree remove --force {path}", clone)
    assert (result.returncode == 0) is allowed, result.stderr


def test_worktree_force_remove_needs_one_existing_path(clone: Path) -> None:
    assert run_hook("git worktree remove --force", clone).returncode == 2
    missing = clone.parent / "no-such-worktree"
    assert run_hook(f"git worktree remove -f {missing}", clone).returncode == 2


def test_worktree_lock_override_is_blocked(clone: Path) -> None:
    path = add_worktree(clone, "locked", "origin/squashed")
    git(clone, "worktree", "lock", str(path))
    assert run_hook(f"git worktree remove -f -f {path}", clone).returncode == 2


def test_mixed_branch_and_worktree_cleanup_needs_both_verified(clone: Path) -> None:
    merged = add_worktree(clone, "mixed-merged", "origin/squashed")
    unmerged = add_worktree(clone, "mixed-unmerged", "origin/unmerged")
    ok = f"git branch -D fast-forwarded && git worktree remove --force {merged}"
    bad = f"git branch -D fast-forwarded && git worktree remove --force {unmerged}"
    assert run_hook(ok, clone).returncode == 0
    assert run_hook(bad, clone).returncode == 2


def test_cd_then_cleanup_is_allowed_when_verified(clone: Path) -> None:
    """Agents commonly write `cd <repo> && ...`; the tracked cwd must let a
    fully merged worktree+branch cleanup through, exactly as `-C` does."""
    merged = add_worktree(clone, "cd-merged", "origin/squashed")
    command = (
        f"cd {clone} && git worktree remove --force {merged} "
        "&& git branch -D fast-forwarded"
    )
    result = run_hook(command, clone.parent)
    assert result.returncode == 0, result.stderr


def test_cd_then_cleanup_is_blocked_when_unmerged(clone: Path) -> None:
    unmerged = add_worktree(clone, "cd-unmerged", "origin/unmerged")
    command = f"cd {clone} && git worktree remove --force {unmerged}"
    result = run_hook(command, clone.parent)
    assert result.returncode == 2


def test_blocked_delete_explains_the_allowed_case(clone: Path) -> None:
    result = run_hook("git branch -D unmerged", clone)
    assert result.returncode == 2
    assert "git fetch first" in result.stderr
