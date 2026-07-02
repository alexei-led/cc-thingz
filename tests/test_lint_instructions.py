"""Tests for src/skills/reviewing-instructions/scripts/lint-instructions.py.

Covers the F-NO-ITALIC/F-NO-HR/F-NO-TABLE fence and inline-code-span bugs:
underscores inside code spans, the 3-tilde fence minimum, and fence-blind
table detection.
"""

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


def _file(lint: ModuleType, body: str):
    return lint.InstructionFile(
        path=Path("dummy.md"),
        rel="dummy.md",
        model="sonnet",
        kind="instruction",
        body=body,
    )


def test_underscore_in_code_span_not_flagged_as_italic(lint: ModuleType) -> None:
    body = (
        "- Use `assert_ne!` and `test_name` in examples.\n"
        "- Also see ``a_b`` for a double-backtick span.\n"
    )
    assert lint.check_f_no_italic(_file(lint, body)) is None


def test_real_italic_outside_code_still_flagged(lint: ModuleType) -> None:
    body = "This has _real italic_ text outside code.\n"
    finding = lint.check_f_no_italic(_file(lint, body))
    assert finding is not None
    assert finding.rule_id == "F-NO-ITALIC"


def test_three_tilde_fence_recognized_hr_inside_not_flagged(lint: ModuleType) -> None:
    body = "~~~\n---\n~~~\n"
    assert lint.check_f_no_hr(_file(lint, body)) is None


def test_piped_command_in_fenced_block_not_flagged_as_table(lint: ModuleType) -> None:
    body = (
        "```sh\n"
        "kubectl get pods | column -t\n"
        "| pod-a | Running | 3/3 |\n"
        "| pod-b | Pending | 0/3 |\n"
        "```\n"
    )
    assert lint.check_f_no_table(_file(lint, body)) is None


def test_real_table_outside_fence_still_flagged(lint: ModuleType) -> None:
    body = "| Col A | Col B |\n| --- | --- |\n| 1 | 2 |\n"
    finding = lint.check_f_no_table(_file(lint, body))
    assert finding is not None
    assert finding.rule_id == "F-NO-TABLE"
