from __future__ import annotations

import json
from pathlib import Path

import pytest
from conftest import _load, dedent_md

generate_release_notes = _load("generate-release-notes.py")


def test_extract_changelog_section_for_version() -> None:
    changelog = dedent_md(
        """
        # Changelog

        ## [Unreleased]

        ## [4.9.0] - 2026-05-19

        ### Added

        - Focused hook execution.

        ### Fixed

        - Compact error output.

        ## [4.8.3] - 2026-05-18

        ### Fixed

        - macOS Bash compatibility.
        """
    )

    assert (
        generate_release_notes.extract_changelog_section(changelog, "4.9.0")
        == dedent_md(
            """
        ### Added

        - Focused hook execution.

        ### Fixed

        - Compact error output.
        """
        ).strip()
    )


def test_extract_changelog_section_requires_matching_version() -> None:
    changelog = "## [4.8.3] - 2026-05-18\n\n### Fixed\n\n- Something.\n"

    with pytest.raises(
        generate_release_notes.ReleaseNotesError, match="missing section"
    ):
        generate_release_notes.extract_changelog_section(changelog, "4.9.0")


def test_extract_changelog_section_rejects_empty_section() -> None:
    changelog = "## [4.9.0] - 2026-05-19\n\n### Added\n\n## [4.8.3] - 2026-05-18\n"

    with pytest.raises(generate_release_notes.ReleaseNotesError, match="is empty"):
        generate_release_notes.extract_changelog_section(changelog, "4.9.0")


def test_build_release_notes_uses_changelog_and_plugin_table() -> None:
    marketplace = {
        "plugins": [{"name": "dev-flow", "description": "Review | lint | commit"}]
    }

    result = generate_release_notes.build_release_notes(
        "### Added\n\n- Faster focused hooks.", marketplace, "alexei-led/cc-thingz"
    )

    assert result.startswith("## Changes\n\n### Added\n\n- Faster focused hooks.")
    assert "| **dev-flow** | Review \\| lint \\| commit |" in result
    assert "agbun build --root ." in result


def test_main_writes_release_notes(tmp_path: Path) -> None:
    changelog = tmp_path / "CHANGELOG.md"
    marketplace = tmp_path / "marketplace.json"
    output = tmp_path / "notes.md"
    changelog.write_text(
        dedent_md(
            """
            ## [4.9.0] - 2026-05-19

            ### Changed

            - Better release notes.
            """
        )
    )
    marketplace.write_text(
        json.dumps(
            {"plugins": [{"name": "dev-flow", "description": "Development workflow"}]}
        )
    )

    status = generate_release_notes.main(
        [
            "--tag",
            "v4.9.0",
            "--changelog",
            str(changelog),
            "--marketplace",
            str(marketplace),
            "--output",
            str(output),
            "--repository",
            "alexei-led/cc-thingz",
        ]
    )

    assert status == 0
    assert "Better release notes" in output.read_text()
