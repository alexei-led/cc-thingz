"""Measure hook startup paths in a temporary home/project, without running linters."""

from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import subprocess
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def measure(runs: int) -> dict:
    with tempfile.TemporaryDirectory(prefix="cc-hook-bench-") as directory:
        project = Path(directory)
        env = {
            "PATH": os.defpath,
            "HOME": directory,
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "SKIP_LINT": "1",
        }
        # The parser is part of the measurement, so require Python on this PATH.
        import shutil

        python = shutil.which("python3")
        if python is None:
            raise RuntimeError("python3 is required")
        bin_dir = project / "bin"
        bin_dir.mkdir()
        (bin_dir / "python3").symlink_to(python)
        env["PATH"] = f"{bin_dir}{os.pathsep}{os.defpath}"
        subprocess.run(
            ["git", "init", "-q", directory],
            env=env,
            check=True,
            capture_output=True,
        )
        (project / "sample.py").touch()
        cases = {
            "file-protector-allow": (
                ["python3", str(ROOT / "src/hooks/file-protector/hook.py")],
                {"tool_input": {"file_path": str(project / "sample.py")}},
            ),
            "smart-lint-input-1MiB": (
                ["bash", str(ROOT / "src/hooks/smart-lint/hook.sh")],
                {
                    "cwd": directory,
                    "session_id": "benchmark",
                    "tool_input": {"file_path": "sample.py", "content": "x" * 1024**2},
                },
            ),
            "test-runner-empty-state": (
                ["bash", str(ROOT / "src/hooks/test-runner/hook.sh")],
                {"cwd": directory, "session_id": "empty"},
            ),
        }
        results = {}
        for name, (command, payload) in cases.items():
            samples = []
            encoded = json.dumps(payload)
            for _ in range(runs):
                start = time.perf_counter()
                subprocess.run(
                    command,
                    input=encoded,
                    text=True,
                    env=env,
                    cwd=project,
                    capture_output=True,
                    timeout=10,
                    check=True,
                )
                samples.append((time.perf_counter() - start) * 1000)
            results[name] = {
                "runs": runs,
                "median_ms": round(statistics.median(samples), 3),
                "min_ms": round(min(samples), 3),
                "max_ms": round(max(samples), 3),
            }
        return {
            "schema_version": 1,
            "platform": platform.system(),
            "python": platform.python_version(),
            "scope": "isolated startup and input handling; no linters or model calls",
            "results": results,
        }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=5)
    args = parser.parse_args()
    if not 1 <= args.runs <= 100:
        parser.error("--runs must be between 1 and 100")
    print(json.dumps(measure(args.runs), indent=2))


if __name__ == "__main__":
    main()
