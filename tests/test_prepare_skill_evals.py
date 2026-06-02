from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from conftest import _load

prepare_skill_evals = _load("prepare-skill-evals.py")


def _write_skill(root: Path, target: str, plugin: str, skill: str, body: str) -> None:
    skill_dir = root / "dist" / target / "plugins" / plugin / "skills" / skill
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(body, encoding="utf-8")


def _write_eval(root: Path, plugin: str, skill: str, count: int = 2) -> None:
    eval_dir = root / "tests" / "skill-evals" / plugin / skill / "evals"
    eval_dir.mkdir(parents=True)
    evals = [
        {
            "id": f"case-{index}",
            "name": f"case {index}",
            "prompt": "describe the workflow",
            "assertions": ["mentions verification", "uses the skill"],
        }
        for index in range(count)
    ]
    (eval_dir / "evals.json").write_text(
        json.dumps({"skill_name": skill, "evals": evals}),
        encoding="utf-8",
    )


def _patch_roots(tmp_path: Path):
    return (
        patch.object(prepare_skill_evals, "ROOT", tmp_path),
        patch.object(prepare_skill_evals, "DIST_DIR", tmp_path / "dist"),
        patch.object(
            prepare_skill_evals, "EVALS_DIR", tmp_path / "tests" / "skill-evals"
        ),
    )


def test_prepare_copies_claude_skill_and_evals(tmp_path):
    _write_skill(tmp_path, "claude", "dev-tools", "writing-shell", "source skill")
    _write_eval(tmp_path, "dev-tools", "writing-shell")
    out = tmp_path.parent / "skill-eval-out-source"

    root_patch, dist_patch, evals_patch = _patch_roots(tmp_path)
    with root_patch, dist_patch, evals_patch:
        skills, evals = prepare_skill_evals.prepare(out, "skills")

    assert (skills, evals) == (1, 2)
    dest = out / "dev-tools" / "skills" / "writing-shell"
    assert (dest / "SKILL.md").read_text(encoding="utf-8") == "source skill"
    assert (dest / "evals" / "evals.json").is_file()


def test_prepare_can_copy_codex_overlay_while_preserving_eval_layout(tmp_path):
    _write_skill(tmp_path, "claude", "dev-tools", "writing-shell", "source skill")
    _write_skill(tmp_path, "codex", "dev-tools", "writing-shell", "codex overlay")
    _write_eval(tmp_path, "dev-tools", "writing-shell", count=1)
    out = tmp_path.parent / "skill-eval-out-codex"

    root_patch, dist_patch, evals_patch = _patch_roots(tmp_path)
    with root_patch, dist_patch, evals_patch:
        skills, evals = prepare_skill_evals.prepare(out, "skills-codex")

    assert (skills, evals) == (1, 1)
    dest = out / "dev-tools" / "skills" / "writing-shell" / "SKILL.md"
    assert dest.read_text(encoding="utf-8") == "codex overlay"


def test_prepare_rejects_repo_output(tmp_path):
    with patch.object(prepare_skill_evals, "ROOT", tmp_path):
        with pytest.raises(
            prepare_skill_evals.EvalPrepError, match="inside the repository"
        ):
            prepare_skill_evals.prepare(tmp_path / "nested", "skills")


def test_prepare_rejects_unknown_source_dir(tmp_path):
    with pytest.raises(prepare_skill_evals.EvalPrepError, match="source directory"):
        prepare_skill_evals.prepare(tmp_path.parent / "out", "flat")
