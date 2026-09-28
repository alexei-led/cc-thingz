from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"


def _source_files() -> list[Path]:
    """Markdown sources plus Agent Bundler sidecar JSON under src/."""
    markdown = SRC.rglob("*.md")
    sidecars = (p for p in SRC.rglob("*.json") if ".agentbundler" in p.parts)
    return sorted(p for p in (*markdown, *sidecars) if p.is_file())


@pytest.mark.parametrize(
    ("banned", "remedy"),
    [
        (
            "mcp__context7__",
            "Use Bash(ctx7 *) / Bash(npx ctx7@latest *) and ctx7 CLI commands.",
        ),
        (
            "mcp__sequential-thinking__",
            "Drop the retired MCP tool reference.",
        ),
    ],
)
def test_sources_do_not_reference_retired_mcp_servers(banned: str, remedy: str):
    files = _source_files()
    assert files, f"no source files found under {SRC}"
    offenders = [
        str(path.relative_to(ROOT)) for path in files if banned in path.read_text()
    ]
    assert not offenders, (
        f"{len(offenders)} file(s) still reference {banned}: "
        + ", ".join(offenders)
        + f". {remedy}"
    )
