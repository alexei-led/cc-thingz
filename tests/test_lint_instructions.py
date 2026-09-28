"""Tests for src/skills/reviewing-instructions/scripts/lint-instructions.py."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest
from conftest import REPO_ROOT

SCRIPT = (
    REPO_ROOT
    / "src"
    / "skills"
    / "reviewing-instructions"
    / "scripts"
    / "lint-instructions.py"
)
GOOD_DESCRIPTION = "Do X. Use when Y. NOT for Z."


def _load_lint_instructions() -> ModuleType:
    spec = importlib.util.spec_from_file_location("lint_instructions", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["lint_instructions"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def lint() -> ModuleType:
    return _load_lint_instructions()


def _rule_ids(
    lint: ModuleType,
    body: str,
    *,
    kind: str = "skill",
    description: str = GOOD_DESCRIPTION,
    name: str = "writing-things",
) -> set[str]:
    item = lint.InstructionFile(
        path=Path(name) / "SKILL.md",
        rel=f"{name}/SKILL.md",
        kind=kind,
        body=body,
        description=description,
        metadata={"name": name},
    )
    return {finding.rule_id for check in lint.ALL_CHECKS if (finding := check(item))}


@pytest.mark.parametrize(
    ("case", "body", "expected"),
    [
        ("clean body", "# Skill\n\nDo the thing.\n", set()),
        ("markdown table", "| A | B |\n| --- | --- |\n| 1 | 2 |\n", set()),
        ("italic and rule", "_Note:_ this.\n\n---\n\n*also* fine.\n", set()),
        ("bold-heavy", "**One**\n**Two**\n**Three**\n", set()),
        ("negative-free body", "Ship small changes.\n", set()),
        ("caps MANDATORY", "Run tests (MANDATORY).\n", {"F-NO-EMPHASIS"}),
        ("caps NEVER", "NEVER push to main.\n", {"F-NO-EMPHASIS"}),
        ("plain never", "Never push to main.\n", set()),
        ("think step by step", "Think step by step.\n", {"F-NO-EMPHASIS"}),
        ("think carefully", "Please think carefully here.\n", {"F-NO-EMPHASIS"}),
        ("caps in inline code", "Match the `CRITICAL` label.\n", set()),
        ("caps in backtick fence", "```\nIMPORTANT: x\n```\n", set()),
        ("caps in tilde fence", "~~~\nMUST do\n~~~\n", set()),
        ("mermaid diagram", "```mermaid\ngraph TD\n```\n", {"F-NO-DIAGRAM"}),
        ("500-line skill", "line\n" * 500, set()),
        ("501-line skill", "line\n" * 501, {"K-PROGRESSIVE"}),
    ],
)
def test_body_rules(lint: ModuleType, case: str, body: str, expected: set[str]) -> None:
    assert _rule_ids(lint, body) == expected, case


@pytest.mark.parametrize(
    ("kind", "description", "name", "expected"),
    [
        ("skill", GOOD_DESCRIPTION, "writing-things", set()),
        ("skill", "Helps with things.", "writing-things", {"K-DESC"}),
        ("skill", GOOD_DESCRIPTION, "Writing_Things", {"K-NAME"}),
        ("skill", GOOD_DESCRIPTION, "a-b", {"K-NAME"}),
        ("instruction", "Helps with things.", "Writing_Things", set()),
    ],
)
def test_frontmatter_rules(
    lint: ModuleType, kind: str, description: str, name: str, expected: set[str]
) -> None:
    body = "Do the thing.\n"
    assert _rule_ids(lint, body, kind=kind, description=description, name=name) == (
        expected
    )


def test_long_non_skill_file_is_not_budgeted(lint: ModuleType) -> None:
    assert _rule_ids(lint, "line\n" * 900, kind="instruction") == set()


def test_frontmatter_model_and_tools_do_not_change_findings(
    lint: ModuleType, tmp_path: Path
) -> None:
    skill = tmp_path / "SKILL.md"
    skill.write_text(
        "---\nname: writing-things\ndescription: Use when X.\n"
        "model: sonnet\nallowed-tools: [Bash, Edit]\n---\n\nShip it.\n"
    )
    item = lint._load(skill, kind="skill", entrypoint=True, origin="test")
    assert item is not None
    assert [check(item) for check in lint.ALL_CHECKS] == [None] * len(lint.ALL_CHECKS)
