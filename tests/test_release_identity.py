from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import REPO_ROOT

CHECKER = REPO_ROOT / "src/skills/releasing-code/scripts/release_notes.py"
TAG = "v6.13.0"
ASSETS = (
    "alexei-led-cc-thingz-claude.tar.gz",
    "alexei-led-cc-thingz-codex.tar.gz",
    "alexei-led-cc-thingz-pi.tgz",
    "alexei-led-cc-thingz-copilot.tar.gz",
    "alexei-led-cc-thingz-cursor.tar.gz",
    "alexei-led-cc-thingz-grok.tar.gz",
)


def _identity(name: str = TAG, **overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "tagName": TAG,
        "name": name,
        "body": "Prior release notes.",
        "isDraft": False,
        "isPrerelease": False,
        "assets": [{"name": asset} for asset in ASSETS],
    }
    value.update(overrides)
    return value


def _run_check(
    tmp_path: Path, identity: dict[str, object], title: str | None = None
) -> subprocess.CompletedProcess[str]:
    path = tmp_path / "release.json"
    path.write_text(json.dumps(identity), encoding="utf-8")
    command = [
        sys.executable,
        str(CHECKER),
        "check-release-identity",
        "--identity",
        str(path),
        "--tag",
        TAG,
    ]
    for asset in ASSETS:
        command.extend(("--expected-asset", asset))
    if title is not None:
        command.extend(("--title", title))
    return subprocess.run(command, capture_output=True, text=True, check=False)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("isDraft", True, "draft"),
        ("isPrerelease", True, "prerelease"),
        ("isDraft", None, "draft"),
        ("isPrerelease", None, "prerelease"),
    ],
)
def test_release_identity_rejects_draft_and_prerelease_targets(
    tmp_path: Path, field: str, value: object, message: str
) -> None:
    result = _run_check(tmp_path, _identity(**{field: value}))

    assert result.returncode != 0
    assert message in result.stderr


def test_repair_accepts_old_title_but_postflight_requires_corrected_title(
    tmp_path: Path,
) -> None:
    old_title = _identity(name="Release 6.13.0")

    before = _run_check(tmp_path, old_title)
    postflight = _run_check(tmp_path, old_title, title=TAG)
    corrected = _run_check(tmp_path, _identity(name=TAG), title=TAG)

    assert before.returncode == 0, before.stderr
    assert postflight.returncode != 0
    assert "title was not updated" in postflight.stderr
    assert corrected.returncode == 0, corrected.stderr


def test_release_identity_rejects_asset_set_drift(tmp_path: Path) -> None:
    identity = _identity()
    identity["assets"] = [{"name": ASSETS[0]}]

    result = _run_check(tmp_path, identity)

    assert result.returncode != 0
    assert "assets do not match" in result.stderr
