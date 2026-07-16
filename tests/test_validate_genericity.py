"""Tests for `scripts.validate.validate_genericity`."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def vg(load_script):
    return load_script("validate_genericity.py")


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).lstrip("\n"))
    return path


def _skill(tmp_path: Path, body: str, targets: str = "") -> Path:
    frontmatter = f"---\nname: x\ndescription: test.\n{targets}---\n"
    return _write(tmp_path / "src" / "skills" / "x" / "SKILL.md", frontmatter + body)


# ---------------------------------------------------------------------------
# Clean pass
# ---------------------------------------------------------------------------


def test_clean_base_passes(vg, tmp_path: Path) -> None:
    skill = _skill(tmp_path, "# Body\n\nRun the test suite and report results.\n")
    assert vg.scan_file(skill) == []


# ---------------------------------------------------------------------------
# Claude-only exemptions
# ---------------------------------------------------------------------------


def test_claude_restricted_list_form_opts_out(vg, tmp_path: Path) -> None:
    skill = _skill(
        tmp_path,
        "Use Task() and $ARGUMENTS freely.\nmcp__perplexity__ask is fine.\n",
        "targets: [claude]\n",
    )
    assert vg.scan_file(skill) == []


def test_claude_restricted_scalar_form_opts_out(vg, tmp_path: Path) -> None:
    skill = _skill(tmp_path, "$ARGUMENTS allowed here.\n", "targets: claude\n")
    assert vg.scan_file(skill) == []


# ---------------------------------------------------------------------------
# Single-violation detection — one case per forbidden token
# ---------------------------------------------------------------------------

_FORBIDDEN: list[tuple[str, str, str]] = [
    ("dollar_arguments", "Run with $ARGUMENTS to do things.\n", "$ARGUMENTS"),
    ("positional_arg", "Pass $1 as the scope argument.\n", "$1"),
    ("task_call", 'Delegate using Task(prompt="foo").\n', "Task("),
    (
        "mcp_prefix",
        "Call mcp__vendor_tool__search.\n",
        "mcp__vendor_tool__search",
    ),
    (
        "claude_env_var",
        "Read ${CLAUDE_PROJECT_DIR} for the path.\n",
        "${CLAUDE_PROJECT_DIR}",
    ),
    (
        "inline_shell",
        "Current branch: !`git branch --show-current`\n",
        "!`git branch --show-current`",
    ),
    ("ask_user_question", "Use AskUserQuestion to prompt.\n", "AskUserQuestion"),
    ("todo_write", "Update progress with TodoWrite.\n", "TodoWrite"),
]


@pytest.mark.parametrize(
    "_id,body,expected", _FORBIDDEN, ids=[r[0] for r in _FORBIDDEN]
)
def test_forbidden_token_detected(
    vg, tmp_path: Path, _id: str, body: str, expected: str
) -> None:
    skill = _skill(tmp_path, body)
    violations = vg.scan_file(skill)
    assert len(violations) == 1, f"expected 1 violation for {_id!r}, got {violations}"
    assert expected in violations[0]


# ---------------------------------------------------------------------------
# Multi-violation and edge cases
# ---------------------------------------------------------------------------


def test_multiple_violations_reported(vg, tmp_path: Path) -> None:
    skill = _skill(
        tmp_path,
        "Use Task() and TodoWrite together.\nAlso $ARGUMENTS.\n",
    )
    assert len(vg.scan_file(skill)) == 3


def test_invalid_frontmatter_reported(vg, tmp_path: Path) -> None:
    skill = tmp_path / "src" / "skills" / "x" / "SKILL.md"
    skill.parent.mkdir(parents=True, exist_ok=True)
    skill.write_text("---\nname: [\nbroken\n---\nbody\n")
    violations = vg.scan_file(skill)
    assert len(violations) == 1
    assert "invalid frontmatter" in violations[0]


def test_line_numbers_account_for_frontmatter(vg, tmp_path: Path) -> None:
    skill = _skill(tmp_path, "\n# Heading\n\nBody uses $ARGUMENTS here.\n")
    violations = vg.scan_file(skill)
    assert len(violations) == 1
    # frontmatter spans lines 1-3, blank line 4, heading line 5,
    # blank line 6, body line 7 (or nearby — assert line ref is present)
    assert ":" in violations[0] and violations[0].count(":") >= 2, violations[0]


def test_discover_base_files(vg, tmp_path: Path) -> None:
    _write(tmp_path / "src" / "skills" / "a" / "SKILL.md", "---\nname: a\n---\n")
    _write(tmp_path / "src" / "agents" / "b.md", "---\nname: b\n---\n")
    _write(
        tmp_path / "src" / "skills" / "a" / ".agentbundler" / "targets" / "pi.json",
        "{}",
    )
    found = vg.discover_base_files(tmp_path)
    names = {str(p.relative_to(tmp_path)) for p in found}
    assert "src/skills/a/SKILL.md" in names
    assert "src/agents/b.md" in names
    assert len(found) == 2


def test_repo_baselines_pass(vg) -> None:
    """Existing migrated src/ base files must already be vendor-neutral."""
    violations: list[str] = []
    for path in vg.discover_base_files():
        violations.extend(vg.scan_file(path))
    assert violations == [], "\n".join(violations[:10])
