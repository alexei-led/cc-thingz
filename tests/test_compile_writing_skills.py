"""Compilation checks for the writing-skills source skill."""

from __future__ import annotations

from pathlib import Path

import frontmatter
import pytest
from conftest import TARGETS, make_batch_skill_staging_root


@pytest.fixture(scope="module")
def cs(load_script):
    load_script("build/compile.py")
    return load_script("build/compile_skill.py")


@pytest.mark.parametrize("target", TARGETS)
def test_writing_skills_compiles_for_target(cs, tmp_path: Path, target: str) -> None:
    root = make_batch_skill_staging_root(tmp_path)
    skill_dir = root / "src" / "skills" / "writing-skills"
    plugin_index = {"writing-skills": ["plugin"]}

    written = cs.compile_skill(skill_dir, target, plugin_index, root)

    assert written, f"compile_skill returned no writes for writing-skills/{target}"

    skill_md = written[0]
    post = frontmatter.loads(skill_md.read_text())
    assert post.metadata.get("name") == "writing-skills"
    assert post.metadata.get("description")
    assert "targets" not in post.metadata

    out_dir = skill_md.parent
    assert (out_dir / "references" / "skill-principles.md").is_file()
    assert (out_dir / "references" / "repo-conventions.md").is_file()
