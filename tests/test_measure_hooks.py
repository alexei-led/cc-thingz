from __future__ import annotations

import json
import subprocess
import sys

from conftest import REPO_ROOT

SCRIPT = REPO_ROOT / "scripts/diagnostics/measure-hooks.py"


def test_hook_measurement_isolated_report():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--runs", "1"],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    report = json.loads(result.stdout)
    assert report["schema_version"] == 1
    assert set(report["results"]) == {
        "file-protector-allow",
        "smart-lint-input-1MiB",
        "test-runner-empty-state",
    }
    for sample in report["results"].values():
        assert sample["runs"] == 1
        assert 0 <= sample["min_ms"] <= sample["max_ms"]


def test_hook_measurement_rejects_unbounded_runs():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--runs", "0"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 2
    assert "between 1 and 100" in result.stderr
