"""Both hooks consume one user-owned checkout profile."""

import json
import os
import subprocess
import sys
from pathlib import Path

from git_helpers import init_repo, run_hook

FILE_HOOK = Path(__file__).resolve().parents[2] / "src/hooks/file-protector/hook.py"


def test_shared_profile_scopes_git_and_file_decisions(tmp_path: Path) -> None:
    project = init_repo(tmp_path / "project")
    other = init_repo(tmp_path / "other")
    config = tmp_path / "policy.json"
    config.write_text(
        json.dumps(
            {
                "projects": {
                    str(project): {
                        "gitGuardrails": {"blockPatterns": [r"^git push .*production"]},
                        "fileProtector": {"allowPaths": ["fixtures/demo.pem"]},
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    env = {**os.environ, "HOME": str(tmp_path), "CLAUDE_HOOK_CONFIG": str(config)}

    def file_decision(root: Path, path: str) -> int:
        return subprocess.run(
            [sys.executable, str(FILE_HOOK)],
            input=json.dumps({"cwd": str(root), "tool_input": {"path": path}}),
            env=env,
            text=True,
            capture_output=True,
            check=False,
        ).returncode

    assert run_hook("git push origin production", project, env).returncode == 2
    assert run_hook("git push origin production", other, env).returncode == 0
    assert file_decision(project, "fixtures/demo.pem") == 0
    assert file_decision(project, "fixtures/other.pem") == 2
    assert file_decision(other, "fixtures/demo.pem") == 2
