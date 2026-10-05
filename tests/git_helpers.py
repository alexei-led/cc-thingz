"""Real Git fixtures and hook boundary helpers shared by cleanup suites."""

import json
import os
import subprocess
from pathlib import Path

HOOK = Path(__file__).resolve().parents[1] / "src/hooks/git-guardrails/hook.sh"
DECIDE = Path(__file__).resolve().parents[1] / "src/hooks/git-guardrails/decide.py"
ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@example.com",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@example.com",
    "CLAUDE_HOOK_CONFIG": "/nonexistent",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_NOSYSTEM": "1",
}


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, env=ENV, check=True, capture_output=True, text=True
    ).stdout.strip()


def create_cleanup_clone(tmp_path: Path) -> Path:
    """Import the same real commit graph in one process, without checkout churn."""
    origin = tmp_path / "origin"
    work = tmp_path / "work"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    commits = [
        ("main", None, "base.txt", "base\n"),
        ("squashed", 1, "a.txt", "a1\n"),
        ("squashed", 2, "a.txt", "a2\n"),
        ("fast-forwarded", 1, "b.txt", "b\n"),
        ("unmerged", 1, "c.txt", "c\n"),
        ("main", 4, "a.txt", "a2\n"),
        ("main", 6, "later.txt", "master moved on\n"),
    ]
    stream = []
    for mark, (branch, parent, filename, content) in enumerate(commits, 1):
        stream.extend(
            [
                f"commit refs/heads/{branch}\nmark :{mark}\n",
                f"committer t <t@example.com> {1700000000 + mark} +0000\n",
                f"data {len(filename)}\n{filename}\n",
            ]
        )
        if parent is not None:
            stream.append(f"from :{parent}\n")
        stream.append(
            f"M 100644 inline {filename}\ndata {len(content.encode())}\n{content}\n"
        )
    subprocess.run(
        ["git", "-C", str(origin), "fast-import", "--quiet"],
        input="".join(stream),
        env=ENV,
        text=True,
        capture_output=True,
        check=True,
    )
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


def add_worktree(clone: Path, name: str, start: str) -> Path:
    path = clone.parent / f"wt-{name}"
    git(clone, "worktree", "add", "-q", "-b", name, str(path), start)
    return path
