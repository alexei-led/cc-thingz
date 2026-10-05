"""Cleanup consent is scoped to one commit and never disables other git guards."""

import json
import os
import subprocess
from pathlib import Path

import pytest
from git_helpers import (
    ENV,
    add_worktree,
    git,
    run_hook,
)

DECIDE = Path(__file__).resolve().parents[2] / "src/hooks/git-guardrails/decide.py"


@pytest.mark.parametrize(
    "command",
    [
        "git push --force-with-lease origin main",
        "git push --force-with-lease=main:deadbeef origin main",
        "git push --mirror origin",
        "git branch -f -d unmerged",
        "git branch --delete -f unmerged",
        "bash --norc -c 'git reset --hard'",
    ],
)
def test_cleanup_does_not_relax_existing_destructive_boundaries(
    clone: Path,
    command: str,
) -> None:
    assert run_hook(command, clone).returncode == 2


def test_consent_cannot_cover_two_branch_targets(clone: Path) -> None:
    git(clone, "branch", "same-tip", "unmerged")
    tip = git(clone, "rev-parse", "unmerged")
    result = run_hook(
        f"git -c cc-thingz.cleanupApproved={tip} branch -D unmerged same-tip",
        clone,
    )
    assert result.returncode == 2


def test_approved_tip_becoming_stale_is_rejected(clone: Path) -> None:
    git(clone, "branch", "moved-after-consent", "unmerged")
    old_tip = git(clone, "rev-parse", "moved-after-consent")
    new_tip = git(
        clone,
        "commit-tree",
        "unmerged^{tree}",
        "-p",
        old_tip,
        "-m",
        "after consent",
    )
    git(clone, "update-ref", "refs/heads/moved-after-consent", new_tip)
    result = run_hook(
        f"git -c cc-thingz.cleanupApproved={old_tip} branch -D moved-after-consent",
        clone,
    )
    assert result.returncode == 2


def test_current_worktree_from_subdirectory_stays_protected(clone: Path) -> None:
    path = add_worktree(clone, "current-subdirectory", "origin/unmerged")
    subdir = path / "inside"
    subdir.mkdir()
    tip = git(path, "rev-parse", "HEAD")
    result = run_hook(
        f"git -c cc-thingz.cleanupApproved={tip} worktree remove --force {path}",
        subdir,
    )
    assert result.returncode == 2


def test_marker_does_not_claim_to_pin_file_contents(clone: Path) -> None:
    path = add_worktree(clone, "file-attestation", "origin/unmerged")
    tip = git(path, "rev-parse", "HEAD")
    (path / "new-file.txt").write_text(
        "agent must recheck this before attesting consent"
    )
    result = run_hook(
        f"git -c cc-thingz.cleanupApproved={tip} worktree remove --force {path}",
        clone,
    )
    assert result.returncode == 0, result.stderr


def test_plain_remove_then_branch_delete(clone: Path) -> None:
    path = add_worktree(clone, "plain-remove", "origin/squashed")
    result = run_hook(
        f"git worktree remove {path} && git branch -D plain-remove", clone
    )
    assert result.returncode == 0, result.stderr


def test_worktree_basename_does_not_hide_untracked_work(clone: Path) -> None:
    path = add_worktree(clone, "basename-dirty", "origin/squashed")
    (path / "draft.txt").write_text("valuable work")
    assert run_hook(f"git worktree remove {path.name}", clone).returncode == 2


def test_untracked_work_is_not_disposable(clone: Path) -> None:
    path = add_worktree(clone, "untracked-work", "origin/squashed")
    (path / "draft.txt").write_text("valuable work")
    assert run_hook(f"git worktree remove --force {path}", clone).returncode == 2


def test_scoped_consent_allows_unmerged_branch(clone: Path) -> None:
    tip = git(clone, "rev-parse", "unmerged")
    result = run_hook(
        f"git -c cc-thingz.cleanupApproved={tip} branch -D unmerged", clone
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("suffix", ["reset --hard", "clean -fdx", "push --force"])
def test_cleanup_consent_does_not_allow_other_destruction(
    clone: Path, suffix: str
) -> None:
    tip = git(clone, "rev-parse", "unmerged")
    assert (
        run_hook(f"git -c cc-thingz.cleanupApproved={tip} {suffix}", clone).returncode
        == 2
    )


def test_wrong_tip_consent_is_rejected(clone: Path) -> None:
    tip = git(clone, "rev-parse", "main")
    assert (
        run_hook(
            f"git -c cc-thingz.cleanupApproved={tip} branch -D unmerged", clone
        ).returncode
        == 2
    )


def test_consent_is_not_read_from_persistent_git_config(clone: Path) -> None:
    git(
        clone,
        "config",
        "cc-thingz.cleanupApproved",
        git(clone, "rev-parse", "unmerged"),
    )
    try:
        assert run_hook("git branch -D unmerged", clone).returncode == 2
    finally:
        git(clone, "config", "--unset", "cc-thingz.cleanupApproved")


def test_consent_never_removes_protected_branch(clone: Path) -> None:
    git(clone, "branch", "develop", "unmerged")
    tip = git(clone, "rev-parse", "develop")
    assert (
        run_hook(
            f"git -c cc-thingz.cleanupApproved={tip} branch -D develop", clone
        ).returncode
        == 2
    )


def test_consent_allows_specifically_approved_dirty_worktree(clone: Path) -> None:
    path = add_worktree(clone, "approved-dirty", "origin/unmerged")
    (path / "draft.txt").write_text("user agreed to discard")
    tip = git(path, "rev-parse", "HEAD")
    result = run_hook(
        f"git -c cc-thingz.cleanupApproved={tip} worktree remove --force {path}", clone
    )
    assert result.returncode == 0, result.stderr


def test_single_force_cannot_override_a_lock_even_with_consent(clone: Path) -> None:
    path = add_worktree(clone, "consent-locked", "origin/unmerged")
    git(clone, "worktree", "lock", str(path))
    tip = git(path, "rev-parse", "HEAD")
    assert (
        run_hook(
            f"git -c cc-thingz.cleanupApproved={tip} worktree remove --force {path}",
            clone,
        ).returncode
        == 2
    )


@pytest.mark.parametrize(
    ("state", "head", "base", "allowed"),
    [
        ("MERGED", "tip", "main", True),
        ("OPEN", "tip", "main", False),
        ("MERGED", "other", "main", False),
        ("MERGED", "tip", "develop", False),
    ],
)
def test_pr_proof_is_bound_to_head_and_base(
    clone: Path, tmp_path: Path, state: str, head: str, base: str, allowed: bool
) -> None:
    tip = git(clone, "rev-parse", "unmerged")
    oid = tip if head == "tip" else git(clone, "rev-parse", "main")
    bindir = tmp_path / "bin"
    bindir.mkdir()
    gh = bindir / "gh"
    gh.write_text(
        "#!/usr/bin/env python3\nimport json\nprint(json.dumps("
        + repr(
            {
                "state": state,
                "headRefOid": oid,
                "baseRefName": base,
                "mergeCommit": {"oid": git(clone, "rev-parse", "main")},
            }
        )
        + "))\n"
    )
    gh.chmod(0o755)
    command = "git branch -D unmerged"
    result = subprocess.run(
        ["bash", str(DECIDE.parent / "hook.sh"), str(DECIDE)],
        input=json.dumps({"cwd": str(clone), "tool_input": {"command": command}}),
        env={**ENV, "PATH": f"{bindir}:{os.environ['PATH']}"},
        capture_output=True,
        text=True,
    )
    assert (result.returncode == 0) is allowed, result.stderr
