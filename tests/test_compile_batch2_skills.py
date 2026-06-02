"""Compilation tests for batch-2 migrated skills (plan Task 16).

Batch-2 skills carry per-target sidecars in the legacy layout
(`SKILL.codex.md`, `SKILL.pi.md`). After migration, each skill lives at
`src/skills/<name>/` with the sidecar bodies installed as overlay bodies under
`<target>/body.md`, and the original Claude SKILL.md preserved as
`claude/body.md` whenever the base was swapped to a vendor-neutral variant.

The suite asserts the migration outcome rather than the byte-level dist
output:

- each multi-target skill compiles to at least one written `SKILL.md` for
  every target
- Claude-only skills (`reviewing-cc-config`, `deploying-infra`,
  `linting-instructions`, `analyzing-usage`) skip non-claude targets through
  the base `targets: [claude]` restriction
- skills migrated via `swap_pi_body` or `swap_claude_body` route the original
  Claude orchestration body to the Claude target while emitting the
  vendor-neutral variant elsewhere
- the genericity validator stays clean for every migrated base
"""

from __future__ import annotations

from pathlib import Path

import frontmatter
import pytest
from conftest import REPO_ROOT, TARGETS, make_batch_skill_staging_root

BATCH_2_ALL_TARGETS = (
    "browser-automation",
    "mem-history",
    "exploring-repos",
    "researching-web",
    "evolving-config",
    "fixing-code",
    "improving-tests",
    "documenting-code",
    "managing-infra",
)

BATCH_2_CLAUDE_ONLY = (
    "reviewing-cc-config",
    "deploying-infra",
)

# Skills migrated via swap_claude_body / swap_pi_body must keep the
# Claude-specific body for Claude. The check looks for any target-specific
# token that appears in claude/body.md only.
# researching-web is intentionally excluded: its Claude "Deep Mode: Agent"
# dispatch block was removed in the 39→3 consolidation (neither surviving role
# has Perplexity MCP in its envelope), so its claude/body.md no longer carries
# a Claude-only orchestration token. It still compiles for all targets and is
# covered by BATCH_2_ALL_TARGETS.
SWAP_SKILLS_AND_CLAUDE_TOKENS = {
    "browser-automation": "claude-in-chrome",
    "exploring-repos": "mcp__deepwiki__",
    "evolving-config": "TaskCreate",
    "documenting-code": "TaskCreate",
    "fixing-code": "TaskCreate",
    "improving-tests": "TaskCreate",
}

_SRC_SKILLS = REPO_ROOT / "src" / "skills"


@pytest.fixture(scope="module")
def cs(load_script):
    load_script("build/compile.py")
    return load_script("build/compile_skill.py")


@pytest.mark.parametrize("skill", BATCH_2_ALL_TARGETS)
@pytest.mark.parametrize("target", TARGETS)
def test_batch2_skill_compiles_for_target(
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


@pytest.mark.parametrize("skill", BATCH_2_CLAUDE_ONLY)
def test_claude_only_skill_skips_other_targets(cs, tmp_path: Path, skill: str) -> None:
    root = make_batch_skill_staging_root(tmp_path)
    skill_dir = root / "src" / "skills" / skill
    plugin_index = {skill: ["plugin"]}

    assert cs.compile_skill(skill_dir, "claude", plugin_index, root), (
        f"{skill} did not emit for claude despite targets: [claude]"
    )
    for t in ("codex", "gemini", "pi"):
        assert cs.compile_skill(skill_dir, t, plugin_index, root) == [], (
            f"{skill} should be skipped for target {t}"
        )


@pytest.mark.parametrize("skill,token", sorted(SWAP_SKILLS_AND_CLAUDE_TOKENS.items()))
def test_swap_skill_routes_claude_body(
    cs, tmp_path: Path, skill: str, token: str
) -> None:
    """Swap-migrated skills must put the Claude orchestration body on Claude only."""
    root = make_batch_skill_staging_root(tmp_path)
    skill_dir = root / "src" / "skills" / skill
    plugin_index = {skill: ["plugin"]}

    claude_written = cs.compile_skill(skill_dir, "claude", plugin_index, root)
    codex_written = cs.compile_skill(skill_dir, "codex", plugin_index, root)

    claude_body = frontmatter.loads(claude_written[0].read_text()).content
    codex_body = frontmatter.loads(codex_written[0].read_text()).content

    assert token in claude_body, (
        f"Claude body for {skill} should retain target-specific token '{token}'"
    )
    assert token not in codex_body, (
        f"Codex body for {skill} must not leak target-specific token '{token}'"
    )


def test_genericity_validator_clean_for_batch2(load_script) -> None:
    """All batch-2 bases pass the vendor-neutral content scan."""
    vg = load_script("validate_genericity.py")

    violations: list[str] = []
    for skill in BATCH_2_ALL_TARGETS + BATCH_2_CLAUDE_ONLY:
        base = _SRC_SKILLS / skill / "SKILL.md"
        violations.extend(vg.scan_file(base))
    assert violations == [], "\n".join(violations)
