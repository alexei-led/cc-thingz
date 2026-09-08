from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import REPO_ROOT

SMART_LINT_ROOT = REPO_ROOT / "src" / "hooks" / "smart-lint"
BASH4_ONLY_PATTERNS = {
    r"\bmapfile\b": "mapfile is Bash 4+; macOS /bin/bash is 3.2",
    r"\breadarray\b": "readarray is Bash 4+; macOS /bin/bash is 3.2",
    r"\b(?:declare|local)\s+-A\b": (
        "associative arrays are Bash 4+; macOS /bin/bash is 3.2"
    ),
}


def test_smart_lint_avoids_bash4_only_features() -> None:
    scripts: list[Path] = sorted(SMART_LINT_ROOT.rglob("*.sh"))
    assert scripts

    for script in scripts:
        text = script.read_text()
        for pattern, reason in BASH4_ONLY_PATTERNS.items():
            assert not re.search(pattern, text), (
                f"{script.relative_to(REPO_ROOT)} uses {reason}"
            )


@pytest.mark.parametrize("pi_runtime", [False, True])
@pytest.mark.parametrize("payload_size", [0, 512 * 1024])
@pytest.mark.parametrize("inherited_input", [False, True])
def test_wrapper_preserves_stdin_file_and_session(
    tmp_path, pi_runtime, payload_size, inherited_input
):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "one.py").touch()
    (tmp_path / "two.py").touch()
    event = {"session_id": "stdin-session", "cwd": str(tmp_path)}
    if pi_runtime:
        payload = {
            "event": "post-tool",
            "piEvent": {**event, "input": {"path": "one.py"}},
        }
    else:
        payload = {**event, "tool_input": {"file_path": "one.py"}}
    tool_input = payload["piEvent"]["input"] if pi_runtime else payload["tool_input"]
    tool_input["content"] = "x" * payload_size
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    python = bin_dir / "python3"
    python.write_text(
        "#!/usr/bin/env bash\n"
        'if [[ -n "${HOOK_INPUT_JSON+x}" ]]; then\n'
        '  printf leaked > "$HOME/payload-exported"\n'
        "fi\n"
        f'exec {shlex.quote(sys.executable)} "$@"\n'
    )
    python.chmod(0o755)
    env = {
        **os.environ,
        "SKIP_LINT": "1",
        "HOME": str(tmp_path),
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
    }
    env.pop("HOOK_INPUT_JSON", None)
    if inherited_input:
        env["HOOK_INPUT_JSON"] = "{}"
    result = subprocess.run(
        ["bash", str(SMART_LINT_ROOT / "hook.sh")],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        cwd=SMART_LINT_ROOT,
        env=env,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert not (tmp_path / "payload-exported").exists()
    state = tmp_path / ".git/cc-thingz/hook-files-stdin-session"
    assert state.read_text() == "one.py\n"
    assert not (state.parent / "hook-files-default").exists()
    if pi_runtime:
        assert json.loads(result.stdout) == {"decision": "allow"}
