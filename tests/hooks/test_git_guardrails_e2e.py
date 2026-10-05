"""End-to-end: a squash-merged branch/worktree cleanup must clear git-
guardrails through the real rendered Claude adapter command, not just
through hook.sh directly."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from conftest import REPO_ROOT
from git_helpers import ENV, git

PLUGIN_ROOT = REPO_ROOT / "dist/claude/git-flow"
HOOKS_JSON = PLUGIN_ROOT / "hooks/hooks.json"


def add_worktree(clone: Path, name: str, branch: str) -> Path:
    path = clone.parent / f"wt-{name}"
    git(clone, "worktree", "add", "-q", str(path), branch)
    return path


def run_through_adapter(command: str, work: Path) -> subprocess.CompletedProcess[str]:
    payload = {
        "hook_event_name": "PreToolUse",
        "session_id": "e2e",
        "cwd": str(work),
        "tool_name": "Bash",
        "tool_input": {"command": command},
    }
    handler_command = json.loads(HOOKS_JSON.read_text())["hooks"]["PreToolUse"][0][
        "hooks"
    ][0]["command"]
    environment = {**ENV, "CLAUDE_PLUGIN_ROOT": str(PLUGIN_ROOT)}
    return subprocess.run(
        ["bash", "-c", handler_command],
        cwd=work,
        env=environment,
        input=json.dumps(payload),
        capture_output=True,
        text=True,
    )


def test_merged_worktree_and_branch_cleanup_is_allowed(clone: Path) -> None:
    path = add_worktree(clone, "merged", "squashed")
    command = (
        f"cd {clone} && git worktree remove --force {path} && git branch -D squashed"
    )
    result = run_through_adapter(command, clone.parent)
    assert result.returncode == 0, result.stdout + result.stderr
    assert '"deny"' not in result.stdout


def test_unmerged_branch_cleanup_is_blocked(clone: Path) -> None:
    command = f"cd {clone} && git branch -D unmerged"
    result = run_through_adapter(command, clone.parent)
    assert result.returncode == 0
    assert '"permissionDecision":"deny"' in result.stdout
