import os
import subprocess
from pathlib import Path

from conftest import REPO_ROOT


def run_eval(
    tmp_path: Path, target: str, judge: str = ""
) -> subprocess.CompletedProcess[str]:
    cli = tmp_path / "eval"
    cli.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$CAPTURE"\n', encoding="utf-8")
    cli.chmod(0o755)
    env = {
        **os.environ,
        "OPENAI_API_KEY": "unused",
        "SKILL_EVAL_TARGET": target,
        "SKILL_EVAL_JUDGE": judge,
        "CAPTURE": str(tmp_path / "args"),
    }
    return subprocess.run(
        [
            "make",
            "skill-evals",
            f"SKILL_EVAL_ROOT={tmp_path / 'root'}",
            f"SKILL_EVAL_WORKSPACE={tmp_path / 'workspace'}",
            f"SKILL_EVAL_CLI={cli}",
        ],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_skill_eval_requires_an_explicit_target(tmp_path: Path) -> None:
    result = run_eval(tmp_path, "")

    assert result.returncode != 0
    assert "SKILL_EVAL_TARGET missing" in result.stderr
    assert not (tmp_path / "args").exists()


def test_skill_eval_defaults_judge_to_target(tmp_path: Path) -> None:
    result = run_eval(tmp_path, "model with spaces")

    assert result.returncode == 0, result.stderr
    args = (tmp_path / "args").read_text(encoding="utf-8").splitlines()
    assert args[args.index("--target") + 1] == "model with spaces"
    assert args[args.index("--judge") + 1] == "model with spaces"


def test_skill_eval_accepts_a_separate_judge(tmp_path: Path) -> None:
    result = run_eval(tmp_path, "target", "judge")

    assert result.returncode == 0, result.stderr
    args = (tmp_path / "args").read_text(encoding="utf-8").splitlines()
    assert args[args.index("--target") + 1] == "target"
    assert args[args.index("--judge") + 1] == "judge"
