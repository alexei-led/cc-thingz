from __future__ import annotations

import importlib.util
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

    result = run(["SELECT * FROM t"], tmp_path, env=env)

    gb = real_bytes / 1024**3
    tb = real_bytes / 1024**4
    cost = tb * 5.00
    assert f"Query will scan: {gb:.2f} GB" in result.stdout, result.stdout
    assert f"Estimated cost: ${cost:.4f}" in result.stdout, result.stdout
    assert "WARNING: Query cost exceeds $1.00" in result.stdout, result.stdout
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
    tb = n / 1024**4
    cost = tb * 5.00
    assert result.returncode == 0, result.stdout + result.stderr
    assert f"Query will scan: {gb:.2f} GB" in result.stdout
    assert f"Estimated cost: ${cost:.4f}" in result.stdout


def test_bq_timeout_fails_loudly(monkeypatch: pytest.MonkeyPatch) -> None:
    """subprocess.run is a system boundary — mock it to raise the timeout
    Popen itself would raise, rather than sleeping for real in a test."""
    module = _load_module()

    def fake_run(*args: object, timeout: float, **kwargs: object) -> None:
        raise subprocess.TimeoutExpired(cmd="bq", timeout=timeout)

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    with pytest.raises(SystemExit, match="timed out"):
        module.estimate_bytes("SELECT 1")
