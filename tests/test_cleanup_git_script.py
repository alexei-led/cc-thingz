from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

import pytest
from conftest import REPO_ROOT

SCRIPT = REPO_ROOT / "src" / "skills" / "cleanup-git" / "scripts" / "cleanup-git.sh"


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


def add_merged_branch(repo: Path, base: str, branch: str = "cleanup-me") -> None:
    git(repo, "checkout", "-b", branch)
    write_commit(repo, f"{branch}.txt", "work\n", branch)
    git(repo, "checkout", base)
    git(repo, "merge", "--no-ff", branch, "-m", f"merge {branch}")


def add_remote(repo: Path, tmp_path: Path, *, name: str = "origin") -> Path:
    origin = tmp_path / f"{name}.git"
    result = run(["git", "clone", "--bare", str(repo), str(origin)], tmp_path)
    assert result.returncode == 0, result.stdout
    git(repo, "remote", "add", name, str(origin))
    git(repo, "fetch", name)
    git(repo, "remote", "set-head", name, "-a")
    return origin


def set_upstream(repo: Path, branch: str, remote: str = "origin") -> None:
    git(repo, "branch", "--set-upstream-to", f"{remote}/{branch}", branch)


def create_worktree(repo: Path, tmp_path: Path, branch: str) -> Path:
    worktree = tmp_path / f"wt-{branch.replace('/', '-')}"
    result = run(["git", "worktree", "add", str(worktree), branch], repo)
    assert result.returncode == 0, result.stdout
    return worktree


def make_gh_stub(
    tmp_path: Path, states: dict[str, tuple[str, str | None] | None]
) -> dict[str, str]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    script = bin_dir / "gh"
    lines = [
        "#!/usr/bin/env python3",
        "import sys",
        "states = {",
    ]
    for branch, value in states.items():
        if value is None:
            lines.append(f"    {branch!r}: None,")
        else:
            state, head = value
            lines.append(f"    {branch!r}: ({state!r}, {head!r}),")
    lines += [
        "}",
        "args = sys.argv[1:]",
        "if len(args) >= 4 and args[:2] == ['pr', 'view']:",
        "    branch = args[2]",
        "    value = states.get(branch)",
        "    if value is None:",
        "        sys.exit(1)",
        "    state, head = value",
        "    sys.stdout.write(state + '\\t' + (head or ''))",
        "    sys.exit(0)",
        "sys.exit(1)",
    ]
    script.write_text("\n".join(lines) + "\n")
    script.chmod(script.stat().st_mode | stat.S_IXUSR)
    return {"PATH": f"{bin_dir}:{os.environ['PATH']}"}


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


def test_apply_refuses_when_fetch_prune_fails(tmp_path: Path) -> None:
    repo = init_repo(tmp_path, "main")
    git(repo, "remote", "add", "origin", str(tmp_path / "missing.git"))

    result = run([str(SCRIPT), "--apply"], repo)

    assert result.returncode == 1
    assert "refusing apply with stale refs" in result.stdout


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


def test_removes_squash_merged_pr_worktree_when_gh_confirms_merged(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path, "main")
    branch = "cleanup-me"
    git(repo, "checkout", "-b", branch)
    write_commit(repo, f"{branch}.txt", "work\n", branch)
    pr_head = git(repo, "rev-parse", branch).strip()
    git(repo, "checkout", "main")
    git(repo, "merge", "--squash", branch)
    git(repo, "commit", "-m", f"squash {branch}")
    worktree = create_worktree(repo, tmp_path, branch)
    env = make_gh_stub(tmp_path, {branch: ("MERGED", pr_head)})

    result = run([str(SCRIPT)], repo, env=env)

    assert result.returncode == 0, result.stdout
    assert f"remove {worktree} ({branch}, PR merged)" in result.stdout
    assert f"skip {branch} (in worktree)" in result.stdout


def test_removes_branch_when_pr_not_found_but_git_ancestry_says_merged(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path, "main")
    add_merged_branch(repo, "main")
    env = make_gh_stub(tmp_path, {"cleanup-me": None})

    result = run([str(SCRIPT)], repo, env=env)

    assert result.returncode == 0, result.stdout
    assert "delete cleanup-me (merged)" in result.stdout


def test_removes_upstream_gone_branch(tmp_path: Path) -> None:
    repo = init_repo(tmp_path, "main")
    add_remote(repo, tmp_path)
    git(repo, "checkout", "-b", "gone-branch")
    git(repo, "push", "-u", "origin", "gone-branch")
    git(repo, "reset", "--hard", "main")
    git(repo, "checkout", "main")
    git(repo, "push", "origin", "--delete", "gone-branch")
    git(repo, "fetch", "origin", "--prune")

    result = run([str(SCRIPT)], repo)

    assert result.returncode == 0, result.stdout
    assert "delete gone-branch (upstream gone)" in result.stdout


def test_keeps_dirty_worktree(tmp_path: Path) -> None:
    repo = init_repo(tmp_path, "main")
    branch = "dirty-branch"
    git(repo, "checkout", "-b", branch)
    write_commit(repo, "dirty.txt", "clean\n", "dirty")
    git(repo, "checkout", "main")
    add_remote(repo, tmp_path)
    git(repo, "push", "-u", "origin", branch)
    worktree = create_worktree(repo, tmp_path, branch)
    (worktree / "dirty.txt").write_text("dirty\n")

    result = run([str(SCRIPT)], repo)

    assert result.returncode == 0, result.stdout
    assert f"KEEP {worktree} ({branch}, dirty)" in result.stdout


def test_skips_protected_and_current_branch(tmp_path: Path) -> None:
    repo = init_repo(tmp_path, "main")
    git(repo, "checkout", "-b", "feature")

    result = run([str(SCRIPT)], repo)

    assert result.returncode == 0, result.stdout
    assert "skip main (protected)" in result.stdout
    assert "skip feature (current branch)" in result.stdout


def test_keeps_merged_pr_branch_with_new_commits_ahead_without_force(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path, "main")
    branch = "cleanup-me"
    git(repo, "checkout", "-b", branch)
    write_commit(repo, f"{branch}.txt", "work\n", branch)
    pr_head = git(repo, "rev-parse", branch).strip()
    git(repo, "checkout", "main")
    git(repo, "merge", "--squash", branch)
    git(repo, "commit", "-m", f"squash {branch}")
    git(repo, "checkout", branch)
    write_commit(repo, "after.txt", "after\n", "after merge")
    git(repo, "checkout", "main")
    env = make_gh_stub(tmp_path, {branch: ("MERGED", pr_head)})

    result = run([str(SCRIPT)], repo, env=env)

    assert result.returncode == 0, result.stdout
    assert "KEEP cleanup-me (PR merged, 1 ahead — use --force)" in result.stdout


def test_without_gh_falls_back_to_git_checks(tmp_path: Path) -> None:
    repo = init_repo(tmp_path, "main")
    add_merged_branch(repo, "main")
    env = {"PATH": "/usr/bin:/bin"}

    result = run([str(SCRIPT)], repo, env=env)

    assert result.returncode == 0, result.stdout
    assert "delete cleanup-me (merged)" in result.stdout


def test_pr_not_found_falls_back_to_active_when_not_merged(tmp_path: Path) -> None:
    repo = init_repo(tmp_path, "main")
    git(repo, "checkout", "-b", "feature")
    write_commit(repo, "feature.txt", "feature\n", "feature")
    git(repo, "checkout", "main")
    env = make_gh_stub(tmp_path, {"feature": None})

    result = run([str(SCRIPT)], repo, env=env)

    assert result.returncode == 0, result.stdout
    assert "skip feature (active)" in result.stdout


def test_unreachable_pr_head_survives_apply_without_force(tmp_path: Path) -> None:
    """Pin: an unreachable/bogus PR head must resolve to 'unknown' ahead, not
    0. Pre-fix, this branch is force-deleted; post-fix it must survive."""
    repo = init_repo(tmp_path, "main")
    branch = "cleanup-me"
    git(repo, "checkout", "-b", branch)
    write_commit(repo, f"{branch}.txt", "work\n", branch)
    git(repo, "checkout", "main")
    git(repo, "merge", "--squash", branch)
    git(repo, "commit", "-m", f"squash {branch}")
    git(repo, "checkout", branch)
    write_commit(repo, "after.txt", "after\n", "after merge")
    git(repo, "checkout", "main")
    bogus_head = "f" * 40
    env = make_gh_stub(tmp_path, {branch: ("MERGED", bogus_head)})

    result = run([str(SCRIPT), "--apply"], repo, env=env)

    assert result.returncode == 0, result.stdout
    assert "ahead unknown" in result.stdout
    assert "git fetch" in result.stdout
    assert "--force" in result.stdout
    branches = git(repo, "branch", "--format=%(refname:short)").splitlines()
    assert branch in branches


def test_reachable_pr_head_at_branch_tip_autocleans_without_force(
    tmp_path: Path,
) -> None:
    """Ergonomics guard: a reachable PR head equal to the branch tip (ahead=0)
    must still auto-clean without --force — the squash-merge fast path."""
    repo = init_repo(tmp_path, "main")
    branch = "cleanup-me"
    git(repo, "checkout", "-b", branch)
    write_commit(repo, f"{branch}.txt", "work\n", branch)
    pr_head = git(repo, "rev-parse", branch).strip()
    git(repo, "checkout", "main")
    git(repo, "merge", "--squash", branch)
    git(repo, "commit", "-m", f"squash {branch}")
    env = make_gh_stub(tmp_path, {branch: ("MERGED", pr_head)})

    result = run([str(SCRIPT), "--apply"], repo, env=env)

    assert result.returncode == 0, result.stdout
    assert "Deleted branch cleanup-me" in result.stdout
    branches = git(repo, "branch", "--format=%(refname:short)").splitlines()
    assert branch not in branches


def test_ancestor_merged_branch_autoescalates_to_D_when_d_refuses(
    tmp_path: Path,
) -> None:
    """Proven-safe path (ahead==0 via verified ref) keeps the -d-then-D
    escalation: git branch -d checks HEAD, not the base branch, so -d can
    still refuse and -D must fire automatically."""
    repo = init_repo(tmp_path, "main")
    git(repo, "checkout", "-b", "other")
    git(repo, "checkout", "main")
    add_merged_branch(repo, "main")
    git(repo, "checkout", "other")

    result = run([str(SCRIPT), "--apply"], repo)

    assert result.returncode == 0, result.stdout
    assert "-d refused after cleanup proof" in result.stdout
    assert "deleting with -D" in result.stdout
    branches = git(repo, "branch", "--format=%(refname:short)").splitlines()
    assert "cleanup-me" not in branches


def test_locked_worktree_removal_failure_still_processes_branches(
    tmp_path: Path,
) -> None:
    """Pin: a single failing `git worktree remove` (e.g. a locked worktree)
    must not abort the script under `set -euo pipefail`. Pre-fix, the failure
    kills the `list_worktrees | while ...` subshell and the pipeline's
    non-zero status aborts the script before the `== branches ==` section
    runs, even though `branch-only` is independently eligible for deletion."""
    repo = init_repo(tmp_path, "main")
    add_merged_branch(repo, "main", "wt-branch")
    worktree = create_worktree(repo, tmp_path, "wt-branch")
    git(repo, "worktree", "lock", str(worktree))
    add_merged_branch(repo, "main", "branch-only")

    result = run([str(SCRIPT), "--apply"], repo)

    assert result.returncode == 0, result.stdout
    assert "warning: failed to remove worktree" in result.stdout
    assert "== branches ==" in result.stdout
    assert "Deleted branch branch-only" in result.stdout
    branches = git(repo, "branch", "--format=%(refname:short)").splitlines()
    assert "branch-only" not in branches
    assert "wt-branch" in branches


def test_unknown_ahead_with_force_goes_straight_to_D(tmp_path: Path) -> None:
    """unknown + --force must skip the -d attempt entirely and go straight
    to -D — limping through -d-then-escalate would print a misleading
    'cleanup proof' message for a branch that was never proven safe."""
    repo = init_repo(tmp_path, "main")
    branch = "cleanup-me"
    git(repo, "checkout", "-b", branch)
    write_commit(repo, f"{branch}.txt", "work\n", branch)
    git(repo, "checkout", "main")
    git(repo, "merge", "--squash", branch)
    git(repo, "commit", "-m", f"squash {branch}")
    git(repo, "checkout", branch)
    write_commit(repo, "after.txt", "after\n", "after merge")
    git(repo, "checkout", "main")
    bogus_head = "e" * 40
    env = make_gh_stub(tmp_path, {branch: ("MERGED", bogus_head)})

    result = run([str(SCRIPT), "--apply", "--force"], repo, env=env)

    assert result.returncode == 0, result.stdout
    assert "-d refused" not in result.stdout
    branches = git(repo, "branch", "--format=%(refname:short)").splitlines()
    assert branch not in branches
