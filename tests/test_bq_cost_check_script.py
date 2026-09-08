from __future__ import annotations

import importlib.util
import json
import os
import stat
import subprocess
from pathlib import Path
from types import ModuleType

import pytest
from conftest import REPO_ROOT

SCRIPT = (
    REPO_ROOT / "src" / "skills" / "operating-infra" / "scripts" / "bq-cost-check.py"
)


def _load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("bq_cost_check", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(
    args: list[str], tmp_path: Path, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(
        [str(SCRIPT), *args],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        stdin=subprocess.DEVNULL,
        check=False,
        env=merged_env,
    )


def make_bq_stub(
    tmp_path: Path, stdout: str, stderr: str, returncode: int = 0
) -> dict[str, str]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    script = bin_dir / "bq"
    script.write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        f"sys.stdout.write({stdout!r})\n"
        f"sys.stderr.write({stderr!r})\n"
        f"sys.exit({returncode!r})\n"
    )
    script.chmod(script.stat().st_mode | stat.S_IXUSR)
    return {"PATH": f"{bin_dir}:{os.environ['PATH']}"}


def test_realistic_banner_before_process_bytes_line_parses_right_number(
    tmp_path: Path,
) -> None:
    """Pin: a version/job-id banner containing a bare numeric token (here
    '2') must not be mistaken for the byte count. Pre-fix, the old
    first-numeric-token scan grabs '2' and silently reports near-zero cost,
    skipping the WARN_USD confirmation gate for a real 2 TB scan."""
    real_bytes = 2_000_000_000_000
    stderr = (
        "BigQuery CLI v2 (job 42)\n"
        "Waiting on bqjob_r1234567890_1 ... (0s) Current status: DONE\n"
        "Query successfully validated. Assuming the tables are not modified, "
        f"running this query will process {real_bytes:,} bytes of data.\n"
    )
    env = make_bq_stub(tmp_path, stdout="[]\n", stderr=stderr)

    result = run(
        ["--price-per-tib", "5", "--max-usd", "1", "SELECT * FROM t"], tmp_path, env=env
    )

    gb = real_bytes / 1024**3
    tb = real_bytes / 1024**4
    cost = tb * 5.00
    assert f"Query will scan: {real_bytes} bytes ({gb:.2f} GiB)" in result.stdout, (
        result.stdout
    )
    assert f"Estimated cost: ${cost:.4f}" in result.stdout, result.stdout
    assert "Threshold exceeded" in result.stderr
    assert result.returncode == 1


def test_unparseable_output_fails_loudly(tmp_path: Path) -> None:
    stderr = "BigQuery CLI v2 (job 42)\nSomething unexpected happened.\n"
    env = make_bq_stub(tmp_path, stdout="", stderr=stderr)

    result = run(["SELECT * FROM t"], tmp_path, env=env)

    assert result.returncode != 0
    assert "Error: could not parse bq output" in result.stderr, result.stderr


def test_happy_json_path_still_works(tmp_path: Path) -> None:
    payload = '[{"statistics": {"query": {"totalBytesProcessed": "500000000"}}}]'
    env = make_bq_stub(tmp_path, stdout=payload, stderr="")

    result = run(["SELECT * FROM t"], tmp_path, env=env)

    n = 500_000_000
    gb = n / 1024**3
    assert result.returncode == 0, result.stdout + result.stderr
    assert f"Query will scan: {n} bytes ({gb:.2f} GiB)" in result.stdout
    assert "Estimated cost" not in result.stdout


def test_bq_timeout_fails_loudly(monkeypatch: pytest.MonkeyPatch) -> None:
    """subprocess.run is a system boundary — mock it to raise the timeout
    Popen itself would raise, rather than sleeping for real in a test."""
    module = _load_module()

    def fake_run(*_args: object, timeout: float, **_kwargs: object) -> None:
        raise subprocess.TimeoutExpired(cmd="bq", timeout=timeout)

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    with pytest.raises(SystemExit, match="timed out"):
        module.estimate_bytes("SELECT 1")


@pytest.mark.parametrize(("limit", "expected"), [(500, 0), (499, 1)])
def test_bytes_threshold_and_json_are_noninteractive(
    tmp_path: Path, limit: int, expected: int
) -> None:
    env = make_bq_stub(tmp_path, '{"totalBytesProcessed":"500"}', "CLI warning\n")
    result = run(["--json", "--max-bytes", str(limit), "SELECT 1"], tmp_path, env)
    assert result.returncode == expected
    payload = json.loads(result.stdout)
    assert payload["bytes_processed"] == 500
    assert payload["estimated_cost_usd"] is None
    assert payload["threshold_exceeded"] is bool(expected)


@pytest.mark.parametrize(
    "args", [["--price-per-tib", "nan"], ["--max-bytes", "-1"], ["--max-usd", "1"]]
)
def test_invalid_cost_options_rejected_before_cloud_call(args: list[str]) -> None:
    with pytest.raises(SystemExit) as error:
        _load_module().main([*args, "SELECT 1"])
    assert error.value.code == 2


def test_location_is_forwarded_to_dry_run(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_module()
    calls = []

    def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, '{"totalBytesProcessed":"0"}', "")

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    assert module.main(["--location", "EU", "SELECT 1"]) == 0
    assert calls[0][:3] == ["bq", "--location=EU", "query"]
    assert "--dry_run" in calls[0]
