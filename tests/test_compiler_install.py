"""Compiler installation uses the release pin unless canary is explicit."""

import os
import subprocess
from pathlib import Path

from conftest import REPO_ROOT


def test_compiler_pin_and_explicit_canary(tmp_path: Path) -> None:
    root = tmp_path / "checkout"
    scripts = root / "scripts" / "setup"
    scripts.mkdir(parents=True)
    source = REPO_ROOT / "scripts/setup/install-agbun.sh"
    script = scripts / source.name
    script.write_bytes(source.read_bytes())
    (root / ".agentbundler-version").write_text("v0.7.0\n")
    binary = tmp_path / "bin"
    binary.mkdir()
    log = tmp_path / "calls"
    go = binary / "go"
    go.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$CALL_LOG"\n')
    go.chmod(0o755)
    env = {**os.environ, "PATH": f"{binary}:{os.environ['PATH']}", "CALL_LOG": str(log)}
    env.pop("GITHUB_PATH", None)
    subprocess.run(["bash", str(script)], env=env, check=True)
    subprocess.run(["bash", str(script), "--canary"], env=env, check=True)
    assert log.read_text().splitlines() == [
        "install github.com/alexei-led/agentbundler/cmd/agbun@v0.7.0",
        "install github.com/alexei-led/agentbundler/cmd/agbun@latest",
    ]
    (root / ".agentbundler-version").write_text("latest\n")
    result = subprocess.run(["bash", str(script)], env=env, capture_output=True)
    assert result.returncode == 2
    assert len(log.read_text().splitlines()) == 2
