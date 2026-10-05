"""Real-git regressions for cleanup's merge proof and base selection."""

from pathlib import Path

from test_cleanup_git_script import (
    SCRIPT,
    add_remote,
    git,
    init_repo,
    make_gh_stub,
    run,
    write_commit,
)


def test_fresh_remote_base_is_used_when_local_base_lags(tmp_path: Path) -> None:
    repo = init_repo(tmp_path, "main")
    add_remote(repo, tmp_path)
    git(repo, "checkout", "-b", "merged-remotely")
    write_commit(repo, "feature.txt", "feature\n", "feature")
    git(repo, "push", "origin", "merged-remotely:main")
    git(repo, "checkout", "main")
    env = make_gh_stub(tmp_path, {})
    result = run([str(SCRIPT)], repo, env)
    assert result.returncode == 0, result.stdout
    assert "base branch: origin/main" in result.stdout
    assert "delete merged-remotely (merged)" in result.stdout


def test_squash_without_gh_is_detected_by_patch_equivalence(tmp_path: Path) -> None:
    repo = init_repo(tmp_path, "main")
    git(repo, "checkout", "-b", "squashed")
    write_commit(repo, "a.txt", "a\n", "first")
    write_commit(repo, "a.txt", "a2\n", "second")
    git(repo, "checkout", "main")
    git(repo, "merge", "--squash", "squashed")
    git(repo, "commit", "-m", "squash")
    result = run([str(SCRIPT), "--apply"], repo, make_gh_stub(tmp_path, {}))
    assert result.returncode == 0, result.stdout
    assert (
        "squashed" not in git(repo, "branch", "--format=%(refname:short)").splitlines()
    )


def test_force_requires_an_explicit_target(tmp_path: Path) -> None:
    repo = init_repo(tmp_path, "main")
    result = run([str(SCRIPT), "--apply", "--force"], repo)
    assert result.returncode == 2
    assert "--force requires --branch" in result.stdout


def test_force_cannot_delete_another_branches_commits(tmp_path: Path) -> None:
    repo = init_repo(tmp_path, "main")
    add_remote(repo, tmp_path)
    for branch in ("approved", "keep-me"):
        git(repo, "checkout", "-b", branch, "main")
        write_commit(repo, branch + ".txt", branch, branch)
        git(repo, "push", "-u", "origin", branch)
        git(repo, "checkout", "main")
        git(repo, "push", "origin", "--delete", branch)
    result = run(
        [str(SCRIPT), "--apply", "--force", "--branch", "approved"],
        repo,
        make_gh_stub(tmp_path, {}),
    )
    assert result.returncode == 0, result.stdout
    branches = git(repo, "branch", "--format=%(refname:short)").splitlines()
    assert "approved" not in branches
    assert "keep-me" in branches


def test_conflict_resolved_squash_uses_pr_proof(tmp_path: Path) -> None:
    repo = init_repo(tmp_path, "main")
    git(repo, "checkout", "-b", "conflicted")
    write_commit(repo, "file.txt", "feature\n", "feature")
    tip = git(repo, "rev-parse", "HEAD").strip()
    git(repo, "checkout", "main")
    write_commit(repo, "file.txt", "main moved\n", "base changed")
    conflict = run(["git", "merge", "--squash", "conflicted"], repo)
    assert conflict.returncode == 1
    write_commit(repo, "file.txt", "resolved both\n", "resolved squash")
    env = make_gh_stub(tmp_path, {"conflicted": ("MERGED", tip)})
    result = run([str(SCRIPT), "--apply"], repo, env)
    assert result.returncode == 0, result.stdout
    assert (
        "conflicted"
        not in git(repo, "branch", "--format=%(refname:short)").splitlines()
    )


def test_ignored_files_survive_cleanup(tmp_path: Path) -> None:
    repo = init_repo(tmp_path, "main")
    git(repo, "checkout", "-b", "merged")
    write_commit(repo, ".gitignore", "local.env\n", "ignore")
    git(repo, "checkout", "main")
    git(repo, "merge", "--ff-only", "merged")
    wt = tmp_path / "wt"
    git(repo, "worktree", "add", str(wt), "merged")
    (wt / "local.env").write_text("valuable local data")
    result = run([str(SCRIPT), "--apply"], repo, make_gh_stub(tmp_path, {}))
    assert result.returncode == 0, result.stdout
    assert (wt / "local.env").exists()
    assert "KEEP" in result.stdout
