from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOOKING_UP_DOCS = ROOT / "src" / "skills" / "looking-up-docs"
BANNED = ("mcp__context7",)


def _docs_lookup_files() -> list[Path]:
    files: list[Path] = []
    if LOOKING_UP_DOCS.is_dir():
        files.extend(path for path in LOOKING_UP_DOCS.rglob("*.md") if path.is_file())
    return sorted(files)


def test_docs_lookup_skill_do_not_reference_removed_context7_mcp():
    files = _docs_lookup_files()
    assert files
    for path in files:
        text = path.read_text()
        for banned in BANNED:
            assert banned not in text, f"{path.relative_to(ROOT)} contains {banned}"


def test_context7_reference_documents_required_commands():
    reference = (LOOKING_UP_DOCS / "references" / "context7-cli.md").read_text()

    assert "ctx7 library <name>" in reference
    assert "ctx7 docs /org/project" in reference
    assert "npx ctx7@latest library" in reference
    assert "Do not include secrets" in reference
    assert "Do not call `ctx7 library` more than 3 times" in reference
    assert "Do not call `ctx7 docs` more than 3 times" in reference


def test_official_sources_reference_documents_ecosystem_sources():
    reference = (LOOKING_UP_DOCS / "references" / "official-sources.md").read_text()

    for source in (
        "pkg.go.dev",
        "docs.python.org",
        "PyPI",
        "npm",
        "docs.rs",
        "Maven Central",
        "NuGet",
        "GitHub",
    ):
        assert source in reference
