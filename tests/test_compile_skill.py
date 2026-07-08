"""Fixture-based golden tests for `scripts.build.compile_skill.compile_skill`.

Three real skills cover the variations the pipeline must handle:

- `committing-code` — base only, no per-target body/frontmatter overlay.
- `reviewing-code` — Claude body overlay in mirror mode (`(\\_+)` suffixes).
- `playwright-skill` — Pi body overlay in full-replacement mode, plus support
  files (`scripts/`, `references/`) the overlay engine must copy across.

Each `(skill, target)` pair has a locked snapshot under
`tests/fixtures/golden_skills/<skill>/<target>/`. The test compiles each skill
into a tmp dist root and diffs the result against the snapshot. Regenerating
goldens: run `uv run python scripts/build/compile.py`, then sync the four
target dirs for the affected skills into `tests/fixtures/golden_skills/`.
"""

from __future__ import annotations

import filecmp
from pathlib import Path

import frontmatter
import pytest
from conftest import REPO_ROOT, TARGETS, make_skill_staging_root

GOLDEN_SKILLS = ("committing-code", "reviewing-code", "playwright-skill")

_GOLDENS = REPO_ROOT / "tests" / "fixtures" / "golden_skills"


@pytest.fixture(scope="module")
def cs(load_script):
    """Load `compile_skill.py` as a module via the shared loader."""
    # compile.py must load first so `compile_skill` can import it.
    load_script("build/compile.py")
    return load_script("build/compile_skill.py")


def _diff_trees(golden: Path, actual: Path) -> list[str]:
    """Return a list of human-readable diffs between two directory trees.

    `.md` files use parsed comparison (frontmatter dict + body) so cosmetic
    YAML formatting differences introduced by the project's auto-formatter
    on the fixture side do not break byte-exact equality. All other files
    fall back to byte comparison.
    """
    diffs: list[str] = []

    golden_files = {p.relative_to(golden) for p in golden.rglob("*") if p.is_file()}
    actual_files = {p.relative_to(actual) for p in actual.rglob("*") if p.is_file()}

    for missing in sorted(golden_files - actual_files):
        diffs.append(f"missing from output: {missing}")
    for extra in sorted(actual_files - golden_files):
        diffs.append(f"unexpected in output: {extra}")

    for rel in sorted(golden_files & actual_files):
        diff = _diff_file(golden / rel, actual / rel, rel)
        if diff is not None:
            diffs.append(diff)
    return diffs


def _norm_body(text: str) -> str:
    """Return non-blank, right-stripped lines joined with `\\n`.

    The project's markdown auto-formatter inserts or removes blank separator
    lines around sections that the compiler does not emit identically. The
    line content is semantically equivalent, so drop blank lines for the
    comparison.
    """
    lines = [line.rstrip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def _diff_file(golden: Path, actual: Path, rel: Path) -> str | None:
    if golden.suffix == ".md":
        golden_post = frontmatter.loads(golden.read_text())
        actual_post = frontmatter.loads(actual.read_text())
        if dict(golden_post.metadata) != dict(actual_post.metadata):
            return (
                f"frontmatter mismatch at {rel}\n"
                f"--- golden meta\n{golden_post.metadata}\n"
                f"+++ actual meta\n{actual_post.metadata}"
            )
        if _norm_body(golden_post.content) != _norm_body(actual_post.content):
            return (
                f"body mismatch at {rel}\n"
                f"--- golden body\n{golden_post.content}\n"
                f"+++ actual body\n{actual_post.content}"
            )
        return None
    if filecmp.cmp(golden, actual, shallow=False):
        return None
    return (
        f"content mismatch at {rel}\n"
        f"--- golden\n{golden.read_text(errors='replace')}\n"
        f"+++ actual\n{actual.read_text(errors='replace')}"
    )


def _stub_preambles(root: Path) -> None:
    preambles = root / "scripts" / "build" / "preambles"
    preambles.mkdir(parents=True, exist_ok=True)
    (preambles / "pi.md").write_text("<!-- pi preamble -->\n")
    (preambles / "platform.md").write_text("<!-- platform preamble -->\n")


@pytest.mark.parametrize("skill", GOLDEN_SKILLS)
@pytest.mark.parametrize("target", TARGETS)
def test_compile_skill_matches_golden(
    cs, tmp_path: Path, skill: str, target: str
) -> None:
    root = make_skill_staging_root(tmp_path)
    skill_dir = root / "src" / "skills" / skill

    # Pin an owning plugin so plugin-grouped targets resolve to the same
    # `dist/<target>/plugins/<plugin>/skills/<skill>/` path as the goldens.
    plugin_index = {skill: ["plugin"]}
    written = cs.compile_skill(skill_dir, target, plugin_index, root)

    assert written, f"compile_skill returned no writes for {skill}/{target}"

    actual_dir = written[0].parent
    golden_dir = _GOLDENS / skill / target

    assert golden_dir.is_dir(), f"missing golden snapshot: {golden_dir}"
    diffs = _diff_trees(golden_dir, actual_dir)
    assert not diffs, "\n\n".join(diffs)


def test_targets_restriction_skips_skill(cs, tmp_path: Path) -> None:
    skill = tmp_path / "skill"
    skill.mkdir()
    (skill / "SKILL.md").write_text(
        "---\nname: claude-only\ndescription: only on claude\n"
        "targets:\n  - claude\n---\n\nbody\n"
    )
    root = tmp_path / "repo"
    root.mkdir()
    # Pass an owning plugin so the claude emission is gated only by the
    # `targets:` restriction, not by missing plugin ownership.
    plugin_index = {"skill": ["alpha"]}

    assert cs.compile_skill(skill, "claude", plugin_index, root) != []
    assert cs.compile_skill(skill, "codex", plugin_index, root) == []
    assert cs.compile_skill(skill, "gemini", plugin_index, root) == []
    assert cs.compile_skill(skill, "pi", plugin_index, root) == []


def test_missing_configured_preamble_raises(cs, tmp_path: Path) -> None:
    """A configured preamble file that is absent must fail the build loudly."""
    with pytest.raises(FileNotFoundError, match="preamble"):
        cs.load_preamble("pi", tmp_path)


def test_targets_string_form_accepted(cs, tmp_path: Path) -> None:
    skill = tmp_path / "skill"
    skill.mkdir()
    (skill / "SKILL.md").write_text(
        "---\nname: pi-only\ndescription: only on pi\ntargets: pi\n---\n\nbody\n"
    )
    root = tmp_path / "repo"
    root.mkdir()
    _stub_preambles(root)

    assert cs.compile_skill(skill, "pi", None, root) != []
    assert cs.compile_skill(skill, "claude", None, root) == []


def test_targets_key_stripped_from_emitted_frontmatter(cs, tmp_path: Path) -> None:
    skill = tmp_path / "skill"
    skill.mkdir()
    (skill / "SKILL.md").write_text(
        "---\n"
        "name: leaks-targets\n"
        "description: targets key must not leak to dist\n"
        "targets:\n  - claude\n  - codex\n"
        "---\n\nbody\n"
    )
    root = tmp_path / "repo"
    root.mkdir()
    plugin_index = {"skill": ["alpha"]}

    written = cs.compile_skill(skill, "claude", plugin_index, root)
    assert len(written) == 1
    text = written[0].read_text()
    assert "targets:" not in text.splitlines()[1:5], text


def test_preamble_injected_for_codex(cs, tmp_path: Path) -> None:
    skill = tmp_path / "skill"
    skill.mkdir()
    (skill / "SKILL.md").write_text(
        "---\nname: preamble-check\n"
        "description: body should be preceded by preamble\n"
        "---\n\n# Body\n"
    )
    root = tmp_path / "repo"
    preambles = root / "scripts" / "build" / "preambles"
    preambles.mkdir(parents=True)
    (preambles / "platform.md").write_text("<!-- platform preamble -->\n")

    plugin_index = {"skill": ["alpha"]}
    written = cs.compile_skill(skill, "codex", plugin_index, root)
    text = written[0].read_text()
    assert "<!-- platform preamble -->" in text
    assert text.index("<!-- platform preamble -->") < text.index("# Body")


def test_preamble_absent_for_claude(cs, tmp_path: Path) -> None:
    skill = tmp_path / "skill"
    skill.mkdir()
    (skill / "SKILL.md").write_text(
        "---\nname: no-banner\ndescription: claude gets no banner\n---\n\n# Body\n"
    )
    root = tmp_path / "repo"
    preambles = root / "scripts" / "build" / "preambles"
    preambles.mkdir(parents=True)
    (preambles / "platform.md").write_text("<!-- BANNER-PLATFORM -->\n")
    (preambles / "pi.md").write_text("<!-- BANNER-PI -->\n")

    plugin_index = {"skill": ["alpha"]}
    written = cs.compile_skill(skill, "claude", plugin_index, root)
    text = written[0].read_text()
    assert "BANNER-PLATFORM" not in text
    assert "BANNER-PI" not in text


def test_plugin_index_routes_to_plugin_dir(cs, tmp_path: Path) -> None:
    skill = tmp_path / "skill_root" / "my-skill"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: routed via plugin index\n---\n\nbody\n"
    )
    root = tmp_path / "repo"
    root.mkdir()
    plugin_index = {"my-skill": ["alpha", "beta"]}

    written = cs.compile_skill(skill, "claude", plugin_index, root)
    parents = {p.parent.parent.parent.name for p in written}
    assert parents == {"alpha", "beta"}, written


def test_flat_layout_ignores_plugin_index(cs, tmp_path: Path) -> None:
    skill = tmp_path / "skill_root" / "my-skill"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: flat path even with index\n---\n\nbody\n"
    )
    root = tmp_path / "repo"
    root.mkdir()
    _stub_preambles(root)
    plugin_index = {"my-skill": ["alpha"]}

    written = cs.compile_skill(skill, "pi", plugin_index, root)
    assert len(written) == 1
    assert written[0] == root / "dist" / "pi" / "skills" / "my-skill" / "SKILL.md"


def test_plugin_grouped_target_skips_unowned_skill(cs, tmp_path: Path) -> None:
    """Unowned skills return no writes for plugin-grouped targets."""
    skill = tmp_path / "skill_root" / "orphan"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "---\nname: orphan\ndescription: no plugin owner\n---\n\nbody\n"
    )
    root = tmp_path / "repo"
    root.mkdir()
    _stub_preambles(root)

    assert cs.compile_skill(skill, "claude", None, root) == []
    assert cs.compile_skill(skill, "codex", None, root) == []
    # Flat targets still emit so vendor-neutral skills reach Pi/Gemini.
    assert cs.compile_skill(skill, "pi", None, root) != []
    assert cs.compile_skill(skill, "gemini", None, root) != []
