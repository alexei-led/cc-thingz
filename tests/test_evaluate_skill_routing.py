from __future__ import annotations

import json
import shutil

import pytest
from conftest import _load

routing = _load("evaluate-skill-routing.py")


def test_cli_reports_actual_hint_mismatches_and_process_exits(tmp_path, capsys):
    hook = tmp_path / "hook.sh"
    hook.write_text(
        "#!/bin/bash\ncat >/dev/null\n"
        "echo '→ Consider skills: writing-go writing-rust'\nexit 3\n"
    )
    fixtures = tmp_path / "cases.json"
    fixtures.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "id": "cross-language",
                        "language": "en",
                        "prompt": "Implement Python code",
                        "required": ["writing-python"],
                        "allowed": ["writing-python", "writing-go"],
                    }
                ]
            }
        )
    )
    assert routing.main(["--hook", str(hook), "--fixtures", str(fixtures)]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["summary"] == {
        "cases": 1,
        "matching_cases": 0,
        "suggested_hints": 2,
        "unexpected_hints": 1,
        "required_hints": 1,
        "missing_hints": 1,
        "allowed_hint_precision": 0.5,
        "required_hint_recall": 0.0,
        "nonzero_hook_exits": 1,
    }
    assert report["cases"][0]["unexpected"] == ["writing-rust"]
    assert report["cases"][0]["missing"] == ["writing-python"]
    assert len(report["hook_sha256"]) == 64
    assert len(report["fixtures_sha256"]) == 64


def test_no_suggestions_does_not_report_perfect_precision(tmp_path):
    hook = tmp_path / "hook.sh"
    hook.write_text("#!/bin/bash\ncat >/dev/null\nexit 0\n")
    cases = [
        {
            "id": "silent",
            "language": "en",
            "prompt": "Hello",
            "required": [],
            "allowed": [],
        }
    ]
    report = routing.evaluate(hook, cases)
    assert report["summary"]["allowed_hint_precision"] is None
    assert report["summary"]["required_hint_recall"] is None
    assert report["summary"]["matching_cases"] == 1


def test_invalid_expectations_fail_before_hook_execution(tmp_path, capsys):
    fixtures = tmp_path / "cases.json"
    fixtures.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "id": "bad",
                        "language": "en",
                        "prompt": "hello",
                        "required": ["writing-go"],
                        "allowed": [],
                    }
                ]
            }
        )
    )
    assert routing.main(["--fixtures", str(fixtures)]) == 1
    assert "required hints must be allowed" in capsys.readouterr().err


def test_real_hook_runs_bilingual_fixture_sample():
    if not shutil.which("jq"):
        pytest.skip("actual hook requires jq")
    cases = routing.load_cases(routing.DEFAULT_FIXTURES)
    sample = [
        case
        for case in cases
        if case["id"] in {"slack-channel", "javascript-await", "ru-python-token"}
    ]
    report = routing.evaluate(routing.DEFAULT_HOOK, sample)
    assert report["summary"]["cases"] == 3
    assert set(report["by_language"]) == {"en", "ru"}
    assert report["summary"]["nonzero_hook_exits"] == 0
