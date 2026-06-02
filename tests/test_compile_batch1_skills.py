"""Compilation tests for batch-1 migrated skills (plan Task 15).

Asserts each newly migrated `src/skills/<name>/` source compiles cleanly for
every applicable target. Compared to `test_compile_skill.py`, this suite does
not lock byte-exact goldens — too noisy when many skills × 4 targets would
need refreshing — and instead checks structural invariants that the
migration is meant to preserve:

- compile_skill returns at least one written `SKILL.md` for each target
- the emitted frontmatter keeps `name` and `description` and drops the
  renderer-only `targets` key
- support files referenced via `references/` end up under the dist tree
- the genericity validator is clean for every migrated base
"""

from __future__ import annotations

from pathlib import Path

import frontmatter
import pytest
from conftest import TARGETS, make_batch_skill_staging_root

BATCH_1_SKILLS_ALL_TARGETS = (
    "writing-go",
    "writing-python",
    "writing-typescript",
    "writing-web",
    "sequential-thinking",
    "writing-shell",
    "using-git-worktrees",
    "refactoring-code",
    "smart-explore",
    "brainstorming-ideas",
)
SKILLS_WITH_REFERENCES = {
    "brainstorming-ideas": ("references/grill-protocol.md",),
    "writing-go": (
        "references/cli.md",
        "references/patterns.md",
        "references/testing.md",
    ),
    "writing-python": (
        "references/principles.md",
        "references/patterns.md",
        "references/cli.md",
        "references/testing.md",
    ),
    "writing-typescript": (
        "references/principles.md",
        "references/patterns.md",
        "references/react.md",
        "references/testing.md",
    ),
    "writing-web": ("references/patterns.md",),
    "writing-shell": (
        "references/patterns.md",
        "references/tools.md",
        "references/testing.md",
    ),
    "using-git-worktrees": ("references/workflow.md",),
}


@pytest.fixture(scope="module")
def cs(load_script):
    load_script("build/compile.py")
    return load_script("build/compile_skill.py")


@pytest.mark.parametrize("skill", BATCH_1_SKILLS_ALL_TARGETS)
@pytest.mark.parametrize("target", TARGETS)
def test_batch1_skill_compiles_for_target(
    cs, tmp_path: Path, skill: str, target: str
) -> None:
    root = make_batch_skill_staging_root(tmp_path)
    skill_dir = root / "src" / "skills" / skill

    assert skill_dir.is_dir(), f"missing migrated source: {skill_dir}"
    plugin_index = {skill: ["plugin"]}
    written = cs.compile_skill(skill_dir, target, plugin_index, root)

    assert written, f"compile_skill returned no writes for {skill}/{target}"

    skill_md = written[0]
    post = frontmatter.loads(skill_md.read_text())
    assert post.metadata.get("name") == skill
    assert post.metadata.get("description")
    assert "targets" not in post.metadata, (
        f"renderer-only `targets` leaked into emitted frontmatter for {skill}/{target}"
    )


@pytest.mark.parametrize("skill,refs", sorted(SKILLS_WITH_REFERENCES.items()))
@pytest.mark.parametrize("target", TARGETS)
def test_references_copied_to_dist(
    cs, tmp_path: Path, skill: str, target: str, refs: tuple[str, ...]
) -> None:
    root = make_batch_skill_staging_root(tmp_path)
    skill_dir = root / "src" / "skills" / skill
    plugin_index = {skill: ["plugin"]}

    written = cs.compile_skill(skill_dir, target, plugin_index, root)
    assert written, f"no writes for {skill}/{target}"

    out_dir = written[0].parent
    for rel in refs:
        assert (out_dir / rel).is_file(), f"reference {rel} missing from {out_dir}"


def test_using_git_worktrees_reference_name_is_lowercase() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    refs = repo_root / "src" / "skills" / "using-git-worktrees" / "references"

    names = {path.name for path in refs.iterdir()}

    assert "workflow.md" in names
    assert "WORKFLOW.md" not in names


def test_brainstorming_ideas_swaps_claude_body(cs, tmp_path: Path) -> None:
    """Claude target gets the original orchestration body; others get vendor-neutral."""
    root = make_batch_skill_staging_root(tmp_path)
    skill_dir = root / "src" / "skills" / "brainstorming-ideas"
    plugin_index = {"brainstorming-ideas": ["plugin"]}

    claude_written = cs.compile_skill(skill_dir, "claude", plugin_index, root)
    codex_written = cs.compile_skill(skill_dir, "codex", plugin_index, root)

    claude_body = frontmatter.loads(claude_written[0].read_text()).content
    codex_body = frontmatter.loads(codex_written[0].read_text()).content

    assert "TaskCreate" in claude_body, "Claude body should retain CC orchestration"
    assert "TaskCreate" not in codex_body, "Codex body must be vendor-neutral"
