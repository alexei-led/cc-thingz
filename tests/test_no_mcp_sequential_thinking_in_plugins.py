from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
BANNED = "mcp__sequential-thinking__"


def _markdown_files() -> list[Path]:
    return sorted(path for path in SRC.rglob("*.md") if path.is_file())


def test_no_mcp_sequential_thinking_anywhere_in_sources():
    """Vendor-neutral sources must not reference the retired MCP server.

    The sequential-thinking MCP server was replaced by the `sequential-thinking`
    skill (src/skills/sequential-thinking/SKILL.md), which produces the same
    numbered/revisable/branchable reasoning artifact via prompting and is
    portable across the enabled Agent Bundler targets.
    """
    files = _markdown_files()
    assert files, f"no markdown files found under {SRC}"
    offenders: list[str] = []
    for path in files:
        if BANNED in path.read_text():
            offenders.append(str(path.relative_to(ROOT)))
    assert not offenders, (
        f"{len(offenders)} file(s) still reference {BANNED}: "
        + ", ".join(offenders)
        + '. Drop the MCP tool reference, add "sequential-thinking" to '
        "skills frontmatter instead, and rewrite body refs to use the skill name."
    )
