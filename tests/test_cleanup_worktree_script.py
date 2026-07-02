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
    / "cleanup-worktree.sh"
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
        "    json_idx = args.index('--json') if '--json' in args else -1",
        "    fields = args[json_idx + 1] if json_idx != -1 else ''",
        "    if 'headRefOid' in fields:",
        "        sys.stdout.write(state + '\\t' + (head or ''))",
        "    else:",
        "        sys.stdout.write(state)",
        "    sys.exit(0)",
        "sys.exit(1)",
    ]
    script.write_text("\n".join(lines) + "\n")
    script.chmod(script.stat().st_mode | stat.S_IXUSR)
    return {"PATH": f"{bin_dir}:{os.environ['PATH']}"}


def test_pin_unreachable_pr_head_refuses_without_force(tmp_path: Path) -> None:
    """Pin: gh reporting MERGED alone must not be trusted. Pre-fix, only
    `state` was fetched and any MERGED report cleaned up unconditionally;
    post-fix, an unreachable/bogus headRefOid must refuse and leave the
    worktree and branch untouched."""
    repo = init_repo(tmp_path, "main")
    branch = "cleanup-me"
    git(repo, "checkout", "-b", branch)
    write_commit(repo, f"{branch}.txt", "work\n", branch)
    git(repo, "checkout", "main")
    worktree = create_worktree(repo, tmp_path, branch)
    write_commit(worktree, "after.txt", "after\n", "after merge")
    bogus_head = "f" * 40
    env = make_gh_stub(tmp_path, {branch: ("MERGED", bogus_head)})

    result = run([str(SCRIPT)], worktree, env=env)

    assert result.returncode == 1, result.stdout
    assert "git fetch" in result.stdout
    assert "--force" in result.stdout
    assert worktree.exists()
    listing = git(repo, "worktree", "list")
    assert str(worktree) in listing
    branches = git(repo, "branch", "--format=%(refname:short)").splitlines()
    assert branch in branches


def test_reachable_pr_head_at_tip_autocleans_without_force(tmp_path: Path) -> None:
    """Ergonomics guard: a reachable PR head equal to the branch tip must
    still auto-clean without --force — the squash-merge flow stays
    automatic."""
    repo = init_repo(tmp_path, "main")
    branch = "cleanup-me"
    git(repo, "checkout", "-b", branch)
    write_commit(repo, f"{branch}.txt", "work\n", branch)
    pr_head = git(repo, "rev-parse", branch).strip()
    git(repo, "checkout", "main")
    worktree = create_worktree(repo, tmp_path, branch)
    env = make_gh_stub(tmp_path, {branch: ("MERGED", pr_head)})

    result = run([str(SCRIPT)], worktree, env=env)

    assert result.returncode == 0, result.stdout
    assert "Done." in result.stdout
    assert not worktree.exists()
    branches = git(repo, "branch", "--format=%(refname:short)").splitlines()
    assert branch not in branches
