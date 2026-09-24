from __future__ import annotations

import json
import subprocess
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

    with pytest.raises(
        generate_release_notes.ReleaseNotesError,
        match="meaningful user-visible content",
    ):
        generate_release_notes.extract_changelog_section(changelog, "4.9.0")


@pytest.mark.parametrize(
    "body",
    [
        "### Changes\n",
        "4.9.0\n",
        "VERSION\n",
        "Release VERSION\n",
        "TODO: add notes\n",
        "[Full Changelog](https://github.com/example/repo/compare/v4.8.3...v4.9.0)\n",
        "Compare changes: https://github.com/example/repo/compare/v4.8.3...v4.9.0\n",
    ],
)
def test_extract_changelog_section_rejects_placeholder_content(body: str) -> None:
    changelog = f"## [4.9.0] - 2026-05-19\n\n{body}"

    with pytest.raises(generate_release_notes.ReleaseNotesError):
        generate_release_notes.extract_changelog_section(changelog, "4.9.0")


def test_extract_changelog_section_accepts_meaningful_one_line_patch() -> None:
    changelog = "## [4.9.0] - 2026-05-19\n\nFix stale cache lookups.\n"

    assert (
        generate_release_notes.extract_changelog_section(changelog, "4.9.0")
        == "Fix stale cache lookups."
    )


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


def test_main_advises_on_budget_without_truncating_notes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    changelog = tmp_path / "CHANGELOG.md"
    marketplace = tmp_path / "marketplace.json"
    output = tmp_path / "notes.md"
    content = " ".join(["Important migration detail"] * 60)
    changelog.write_text(f"## [4.9.0] - 2026-05-19\n\n{content}\n")
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
            "--budget",
            "patch",
        ]
    )

    assert status == 0
    assert "Important migration detail" in output.read_text()
    assert output.read_text().count("Important migration detail") == 60
    assert "advisory budget exceeded" in capsys.readouterr().err


def test_main_appends_compare_link_only_for_verified_previous_tag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True
    )
    (tmp_path / "anchor.txt").write_text("release fixture\n")
    subprocess.run(["git", "add", "anchor.txt"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-qm", "previous release"], cwd=tmp_path, check=True
    )
    subprocess.run(["git", "tag", "v4.8.3"], cwd=tmp_path, check=True)
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text("## [4.9.0] - 2026-05-19\n\nFix stale cache lookups.\n")
    marketplace = tmp_path / "marketplace.json"
    marketplace.write_text(
        json.dumps(
            {"plugins": [{"name": "dev-flow", "description": "Development workflow"}]}
        )
    )
    output = tmp_path / "notes.md"
    monkeypatch.chdir(tmp_path)

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
            "--previous-tag",
            "v4.8.3",
        ]
    )

    notes = output.read_text()
    assert status == 0
    assert "## Full Changelog" in notes
    assert notes.endswith(
        "https://github.com/alexei-led/cc-thingz/compare/v4.8.3...v4.9.0\n"
    )

    missing_output = tmp_path / "unverified.md"
    status = generate_release_notes.main(
        [
            "--tag",
            "v4.9.0",
            "--changelog",
            str(changelog),
            "--marketplace",
            str(marketplace),
            "--output",
            str(missing_output),
            "--repository",
            "alexei-led/cc-thingz",
            "--previous-tag",
            "v4.8.2",
        ]
    )
    assert status == 1
    assert not missing_output.exists()


def test_notes_repair_uses_later_changelog_source_and_tagged_package_metadata(
    tmp_path: Path,
) -> None:
    release_target = tmp_path / "release-target"
    packages_dir = release_target / "src/.agentbundler/packages"
    packages_dir.mkdir(parents=True)
    (packages_dir / "dev-flow.json").write_text(
        json.dumps(
            {
                "id": "dev-flow",
                "metadata": {"description": "Description from tagged release"},
            }
        )
    )
    (release_target / "CHANGELOG.md").write_text(
        "## [6.13.0] - 2026-09-24\n\n- Original release note.\n"
    )
    notes_source = tmp_path / "notes-source/CHANGELOG.md"
    notes_source.parent.mkdir()
    notes_source.write_text(
        "## [6.13.0] - 2026-09-24\n\n- Corrected migration detail after release.\n"
    )
    output = tmp_path / "repaired-notes.md"

    status = generate_release_notes.main(
        [
            "--tag",
            "v6.13.0",
            "--changelog",
            str(notes_source),
            "--packages-dir",
            str(packages_dir),
            "--output",
            str(output),
            "--repository",
            "alexei-led/cc-thingz",
        ]
    )

    notes = output.read_text()
    assert status == 0
    assert "Corrected migration detail after release." in notes
    assert "Original release note." not in notes
    assert "Description from tagged release" in notes


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
