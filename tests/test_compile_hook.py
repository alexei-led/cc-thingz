"""Tests for the src/hooks discovery layout.

Asserts every hook has well-formed metadata, executable bits are preserved,
and support directories (e.g. `smart-lint/`) are mirrored under the hook root.
"""

from __future__ import annotations

import stat
from pathlib import Path

import pytest
import yaml
from conftest import REPO_ROOT

REPO = REPO_ROOT

VALID_EVENTS = frozenset(
    {
        "sessionstart",
        "preedit",
        "postedit",
        "prebash",
        "posttool",
        "agentstop",
        "userpromptsubmit",
        "notification",
        "worktreecreate",
        "worktreeremove",
        "exitplanmode",
    }
)

EXPECTED_HOOK_NAMES = frozenset(
    {
        "file-protector",
        "git-guardrails",
        "smart-lint",
        "session-start",
        "skill-enforcer",
        "notify",
        "test-runner",
        "worktree-create",
        "worktree-remove",
        "revdiff-plan-review",
    }
)


def hook_dirs(root: Path) -> list[Path]:
    src = root / "src" / "hooks"
    return sorted(p for p in src.iterdir() if p.is_dir())


def load_meta(hook_dir: Path) -> dict:
    return yaml.safe_load((hook_dir / "meta.yaml").read_text())


def test_repo_has_all_expected_hook_dirs():
    names = {p.name for p in hook_dirs(REPO)}
    assert names == EXPECTED_HOOK_NAMES


def test_every_hook_has_script_and_meta():
    for hook_dir in hook_dirs(REPO):
        assert (hook_dir / "meta.yaml").is_file(), hook_dir
        scripts = list(hook_dir.glob("hook.*"))
        assert len(scripts) == 1, f"{hook_dir} should have exactly one hook.*"
        assert scripts[0].suffix in {".sh", ".py"}


@pytest.mark.parametrize("hook_dir", hook_dirs(REPO), ids=lambda p: p.name)
def test_meta_required_fields(hook_dir: Path):
    meta = load_meta(hook_dir)
    assert meta["name"] == hook_dir.name
    assert meta["event"] in VALID_EVENTS
    assert isinstance(meta["timeout"], int) and meta["timeout"] > 0
    if "status_message" in meta:
        assert isinstance(meta["status_message"], str) and meta["status_message"]
    if "targets" in meta:
        assert isinstance(meta["targets"], list)
        assert all(isinstance(target, str) for target in meta["targets"])


def test_hook_scripts_are_executable():
    for hook_dir in hook_dirs(REPO):
        script = next(hook_dir.glob("hook.*"))
        mode = script.stat().st_mode
        assert mode & stat.S_IXUSR, f"{script} should have user-exec bit"


def test_smart_lint_support_dir_mirrored():
    sub = REPO / "src" / "hooks" / "smart-lint" / "smart-lint"
    assert sub.is_dir()
    expected = {
        "lib.sh",
        "lint-csharp.sh",
        "lint-go.sh",
        "lint-java-kotlin.sh",
        "lint-python.sh",
        "lint-rust.sh",
        "lint-shell.sh",
        "lint-typescript.sh",
        "lint-web.sh",
        "main.sh",
    }
    assert {p.name for p in sub.iterdir()} == expected
    assert sub.joinpath("main.sh").stat().st_mode & stat.S_IXUSR


def test_session_start_is_python_hook():
    hook_dir = REPO / "src" / "hooks" / "session-start"
    assert (hook_dir / "hook.py").is_file()
    assert not (hook_dir / "hook.sh").exists()


def test_known_event_assignments():
    expected = {
        "file-protector": ("preedit", None),
        "git-guardrails": ("prebash", "Checking git command"),
        "smart-lint": ("postedit", "Running smart-lint"),
        "session-start": ("sessionstart", "Loading session context"),
        "skill-enforcer": ("userpromptsubmit", None),
        "test-runner": ("agentstop", "Running targeted tests"),
        "notify": ("notification", None),
        "worktree-create": ("worktreecreate", None),
        "worktree-remove": ("worktreeremove", None),
        "revdiff-plan-review": ("exitplanmode", "Reviewing plan with revdiff"),
    }
    for hook_dir in hook_dirs(REPO):
        meta = load_meta(hook_dir)
        want_event, want_msg = expected[hook_dir.name]
        assert meta["event"] == want_event, hook_dir.name
        assert meta.get("status_message") == want_msg, hook_dir.name


def test_meta_yaml_is_round_trippable():
    """meta.yaml must parse to a dict with the four required fields."""
    for hook_dir in hook_dirs(REPO):
        data = yaml.safe_load((hook_dir / "meta.yaml").read_text())
        assert isinstance(data, dict)
        assert set(data) >= {"name", "event", "timeout"}


def test_no_world_writable_scripts():
    """Defensive: copied scripts must not gain world-writable bits."""
    for hook_dir in hook_dirs(REPO):
        for path in hook_dir.rglob("*"):
            if path.is_file():
                assert not (path.stat().st_mode & stat.S_IWOTH), path


def test_status_message_present_when_expected():
    must_have = {
        "git-guardrails",
        "smart-lint",
        "session-start",
        "test-runner",
        "revdiff-plan-review",
    }
    for hook_dir in hook_dirs(REPO):
        meta = load_meta(hook_dir)
        if hook_dir.name in must_have:
            assert meta.get("status_message"), hook_dir.name


@pytest.mark.parametrize("hook_dir", hook_dirs(REPO), ids=lambda p: p.name)
def test_hook_dir_has_no_unexpected_files(hook_dir: Path):
    """Source layout: only hook.*, meta.yaml, and known support dirs allowed."""
    allowed_files = {"meta.yaml"}
    allowed_files.update({f"hook{ext}" for ext in (".sh", ".py")})
    for entry in hook_dir.iterdir():
        if entry.is_dir():
            continue
        assert entry.name in allowed_files, f"unexpected file: {entry}"
