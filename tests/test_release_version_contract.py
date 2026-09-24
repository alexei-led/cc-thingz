from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from conftest import REPO_ROOT

CHECKER = REPO_ROOT / "src/skills/releasing-code/scripts/release_notes.py"
TAG = "v6.13.0"


def _write_release_fixture(root: Path, package_version: str) -> Path:
    (root / "src/.agentbundler/packages").mkdir(parents=True)
    (root / "src/skills/playwright-skill/scripts").mkdir(parents=True)
    (root / "pyproject.toml").write_text(
        '[project]\nname = "cc-thingz"\n'
        f'version = "{package_version}"\n'
        'requires-python = ">=3.12"\n'
    )
    (root / "uv.lock").write_text(
        'version = 1\nrevision = 3\nrequires-python = ">=3.12"\n\n'
        '[[package]]\nname = "cc-thingz"\n'
        f'version = "{package_version}"\n'
        'source = { virtual = "." }\n'
    )
    (root / "agentbundle.json").write_text(
        json.dumps(
            {
                "distribution": {"version": package_version},
                "composition": [
                    {"aggregate": {"metadata": {"version": package_version}}}
                ],
            }
        )
    )
    (root / "package.json").write_text(json.dumps({"version": package_version}))
    (root / "src/skills/playwright-skill/scripts/package.json").write_text(
        json.dumps({"version": package_version})
    )
    (root / "src/.agentbundler/packages/dev-flow.json").write_text(
        json.dumps({"metadata": {"version": package_version}})
    )
    changelog = root / "CHANGELOG.md"
    changelog.write_text(
        "## [6.13.0] - 2026-09-24\n\n- Corrected the release workflow.\n"
    )
    return changelog


def _run_check_release(root: Path, changelog: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(CHECKER),
            "check-release",
            "--root",
            str(root),
            "--tag",
            TAG,
            "--changelog",
            str(changelog),
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def test_matching_changelog_cannot_mask_synchronized_old_package_versions(
    tmp_path: Path,
) -> None:
    changelog = _write_release_fixture(tmp_path, "6.12.0")
    notes_check = subprocess.run(
        [
            sys.executable,
            str(CHECKER),
            "check-changelog",
            "--changelog",
            str(changelog),
            "--version",
            "6.13.0",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    result = _run_check_release(tmp_path, changelog)

    assert notes_check.returncode == 0
    assert result.returncode != 0
    assert "release tag v6.13.0 does not match" in result.stderr
    assert "6.12.0" in result.stderr


def test_release_contract_rejects_one_drifted_manifest(tmp_path: Path) -> None:
    changelog = _write_release_fixture(tmp_path, "6.13.0")
    package = tmp_path / "src/.agentbundler/packages/dev-flow.json"
    package.write_text(json.dumps({"metadata": {"version": "6.12.0"}}))

    result = _run_check_release(tmp_path, changelog)

    assert result.returncode != 0
    assert "release version manifests disagree" in result.stderr
    assert "6.12.0" in result.stderr


def test_release_contract_rejects_uv_lock_version_drift(tmp_path: Path) -> None:
    changelog = _write_release_fixture(tmp_path, "6.13.0")
    lock = tmp_path / "uv.lock"
    lock.write_text(
        lock.read_text().replace('version = "6.13.0"', 'version = "6.12.0"')
    )

    result = _run_check_release(tmp_path, changelog)

    assert result.returncode != 0
    assert "release version manifests disagree" in result.stderr
    assert "uv.lock=6.12.0" in result.stderr


def test_later_notes_source_is_validated_against_tagged_release_metadata(
    tmp_path: Path,
) -> None:
    target_changelog = _write_release_fixture(tmp_path / "release-target", "6.13.0")
    target_changelog.write_text(
        "## [6.13.0] - 2026-09-24\n\n- Original release note.\n"
    )
    source = tmp_path / "notes-source/CHANGELOG.md"
    source.parent.mkdir()
    source.write_text(
        "## [6.13.0] - 2026-09-24\n\n- Corrected after-tag migration detail.\n"
    )

    result = _run_check_release(target_changelog.parent, source)

    assert result.returncode == 0, result.stderr


def test_release_contract_accepts_matching_manifests_and_notes(
    tmp_path: Path,
) -> None:
    changelog = _write_release_fixture(tmp_path, "6.13.0")

    result = _run_check_release(tmp_path, changelog)

    assert result.returncode == 0, result.stderr
    assert "release notes:" in result.stdout
