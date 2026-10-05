"""git-guardrails lets agents delete merged branches, including squash merges."""

from pathlib import Path

import pytest
from git_helpers import add_worktree, git, run_hook


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
