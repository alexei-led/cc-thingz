"""Table-driven regression coverage for git-guardrails' destructive-op
detection: every case here is either a false positive reported from 30 days
of hook logs, or a bypass the rewrite must still catch.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[2] / "src/hooks/git-guardrails/hook.sh"
DECIDE = Path(__file__).resolve().parents[2] / "src/hooks/git-guardrails/decide.py"

RELEASE_SCRIPT = """\
set -e
cd /tmp/repo
git add -A && git commit -q -m "chore(release): v1.2.3"
GIT_SSH_COMMAND="ssh -o ServerAliveInterval=20" git push -q -u origin HEAD
PR=$(gh pr create --base master --title "chore(release): v1.2.3" --body "notes")
gh pr merge "$PR" --squash --delete-branch; echo MERGED
cd /tmp/repo
git worktree remove ../repo.worktrees/release-1.2.3 2>/dev/null || true
git fetch -q origin && git merge -q --ff-only origin/master
scripts/release/release-tag finalize v1.2.3 | tail -2
GIT_SSH_COMMAND="ssh -o ServerAliveInterval=20" git push origin refs/tags/v1.2.3
"""

HEREDOC_COMMAND = "cat <<'EOF'\nnever run git reset --hard on main\nEOF\n"

MUST_BLOCK = [
    ("git switch --discard-changes main", "switch discarding local changes"),
    ("git switch -f main", "switch -f discards local changes"),
    ("git checkout -qf main", "checkout force inside a short-flag cluster"),
    ("X=$(git reset --hard)", "command substitution runs git"),
    ("echo `git clean -fdx`", "backtick substitution runs git"),
    ("cat <(git push --force origin main)", "process substitution runs git"),
    ("echo ok\ngit reset --hard", "destructive command on a later line"),
    ("true\n\ngit push --force origin main", "force push after a blank line"),
    ('for b in x y; do git branch -D "$b"; done', "unmerged branch inside a for-loop"),
    ("if true; then git reset --hard; fi", "reset --hard inside an if/then"),
    ("sudo git clean -fdx", "sudo-prefixed combined short flags"),
    ("bash -c 'git push --force'", "force push wrapped in bash -c"),
    ("git -C d branch -D unmerged", "unmerged branch via -C"),
    ("git clean -fdx", "clean with combined short flags"),
    ("git push origin +main", "+refspec force push"),
    (
        "GIT_SSH_COMMAND=x git push --force",
        "VAR=value prefix does not hide force push",
    ),
    # Adversarial review: an unrecognized wrapper command must not hide a
    # git invocation from evaluation (allowlisting known prefixes was the
    # bug - these wrappers were never on any list).
    (
        "nice git reset --hard",
        "unrecognized wrapper (nice) does not hide reset --hard",
    ),
    (
        "timeout 30 git push --force",
        "unrecognized wrapper (timeout N) does not hide force push",
    ),
    ("eval git reset --hard", "eval's bare-word argument is still evaluated"),
    (
        'eval "git reset --hard"',
        "eval's quoted argument is tokenized and evaluated",
    ),
    (
        "exec git clean -fdx",
        "unrecognized wrapper (exec) does not hide clean --force",
    ),
    (
        "nohup git reset --hard",
        "unrecognized wrapper (nohup) does not hide reset --hard",
    ),
    (
        "g\\it reset --hard",
        "backslash-split git still resolves to git after unquoting",
    ),
    (
        'g""it push --force',
        "empty-quote-split git still resolves to git after unquoting",
    ),
    (
        "g'i't clean -fdx",
        "single-quote-split git still resolves to git after unquoting",
    ),
    (
        "(git reset --hard) | git branch -fd x | git push -fu origin b",
        "subshell parens and combined short-flag clusters (-fd, -fu)",
    ),
    # Case-insensitive command matching: on macOS's default case-insensitive
    # filesystem, these all resolve to and run the real git binary.
    ("GIT reset --hard", "uppercase GIT still resolves to the real binary"),
    ("Git push --force", "title-case Git still resolves to the real binary"),
    ("gIt clean -fdx", "mixed-case gIt still resolves to the real binary"),
    (
        "/usr/bin/GIT checkout -- .",
        "uppercase GIT behind an absolute path still resolves",
    ),
    (
        "timeout 30 GIT push --force",
        "unrecognized wrapper does not hide an uppercase GIT",
    ),
    (
        "bash -c 'GIT reset --hard'",
        "uppercase GIT inside a bash -c script is still tokenized",
    ),
    (
        "BASH -c 'git push --force'",
        "uppercase BASH -c still resolves to the real interpreter",
    ),
    # ANSI-C/locale quoting (`$'git'`, `$"git"`) shlex-tokenizes to a bare
    # `$git` with no `(` for SUBST_OPENER to strip, but bash expands both to
    # the plain word `git` and runs it for real.
    (
        "$'git' reset --hard",
        "ANSI-C quoting ($'git') still resolves to the real binary",
    ),
    (
        "$'GIT' push --force",
        "ANSI-C quoting of an uppercase GIT still resolves",
    ),
    (
        '$"git" clean -fdx',
        'locale quoting ($"git") still resolves to the real binary',
    ),
    (
        "BASH -c \"$'git' reset --hard\"",
        "ANSI-C quoting inside an uppercase BASH -c script is still tokenized",
    ),
]

MUST_ALLOW = [
    (
        "git worktree remove ../wt 2>/dev/null; git fetch && git merge --ff-only",
        "worktree remove then fetch/merge --ff-only on one line",
    ),
    (
        "git checkout main && git pull --ff-only",
        "checkout then pull --ff-only on one line",
    ),
    ("git pull --ff-only", "plain pull --ff-only"),
    ("git merge --ff-only origin/master", "plain merge --ff-only"),
    ("git worktree remove ../fix-foo", "worktree remove without force"),
    (
        "git -C /repo worktree remove /repo.worktrees/skill-enforcer-fast",
        "worktree remove without force, path contains -fast",
    ),
    ("git checkout -- README.md", "checkout of a path after --"),
    (
        "git checkout --conflict=merge -- f",
        "checkout --conflict=merge is not --force",
    ),
    ("git log --format=%H", "--format is not -f/--force"),
    (
        'git commit -m "docs: never run git push --force"',
        "dangerous text inside a commit message",
    ),
    (HEREDOC_COMMAND, "dangerous text inside a heredoc body"),
    (RELEASE_SCRIPT, "sanitized multi-line release script"),
    ("echo GITHUB_TOKEN", "a word containing GIT that isn't a command (env var name)"),
    ("ls GIT_NOTES", "a word containing GIT that isn't a command (path argument)"),
    (
        'git commit -m "GIT PUSH --FORCE is dangerous, never run it"',
        "uppercase git text inside a commit message",
    ),
    (
        "cat <<'EOF'\nGIT RESET --HARD\nEOF\n",
        "uppercase git text inside a heredoc body",
    ),
]


def run_hook(command: str, tmp_path: Path) -> subprocess.CompletedProcess[str]:
    payload = json.dumps({"tool_input": {"command": command}, "cwd": str(tmp_path)})
    return subprocess.run(
        ["bash", str(HOOK), str(DECIDE)],
        input=payload,
        capture_output=True,
        text=True,
    )


BLOCK_IDS = [reason for _, reason in MUST_BLOCK]
ALLOW_IDS = [reason for _, reason in MUST_ALLOW]


@pytest.mark.parametrize(("command", "reason"), MUST_BLOCK, ids=BLOCK_IDS)
def test_must_block(command: str, reason: str, tmp_path: Path) -> None:
    result = run_hook(command, tmp_path)
    assert result.returncode == 2, f"{reason}: expected block, got {result.stderr}"


@pytest.mark.parametrize(("command", "reason"), MUST_ALLOW, ids=ALLOW_IDS)
def test_must_allow(command: str, reason: str, tmp_path: Path) -> None:
    result = run_hook(command, tmp_path)
    assert result.returncode == 0, f"{reason}: expected allow, got {result.stderr}"
