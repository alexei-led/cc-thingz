from __future__ import annotations

import os
import subprocess
from pathlib import Path

from conftest import REPO_ROOT

SCRIPTS = REPO_ROOT / "src" / "skills" / "documenting-code" / "scripts"
CHECK_LINKS = SCRIPTS / "check-links.py"
PROSE_LINT = SCRIPTS / "prose-lint.py"
RENDER_MERMAID = SCRIPTS / "render-mermaid.sh"


def run(
    args: list[str], cwd: Path, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        env=env,
    )


def test_check_links_accepts_valid_links_and_github_slugs(tmp_path: Path) -> None:
    (tmp_path / "guide.md").write_text(
        "# Guide\n\n## Read `/app:status`\n\n## Setup\n\n## Setup\n\ntext\n",
        encoding="utf-8",
    )
    (tmp_path / "README.md").write_text(
        "See [status](guide.md#read-appstatus), [second setup](guide.md#setup-1),\n"
        "[top](#readme), [site](https://example.com/x#y).\n\n# README\n",
        encoding="utf-8",
    )
    result = run(["python3", str(CHECK_LINKS), "."], tmp_path)
    assert result.returncode == 0, result.stdout
    assert "0 broken" in result.stdout


def test_check_links_reports_missing_file_and_anchor(tmp_path: Path) -> None:
    (tmp_path / "guide.md").write_text("# Guide\n", encoding="utf-8")
    (tmp_path / "README.md").write_text(
        "[gone](missing.md) and [bad](guide.md#nope)\n\n"
        "```md\n[ignored](nowhere.md)\n```\n",
        encoding="utf-8",
    )
    result = run(["python3", str(CHECK_LINKS), "README.md"], tmp_path)
    assert result.returncode == 1
    assert "missing file: missing.md" in result.stdout
    assert "missing anchor: guide.md#nope" in result.stdout
    assert "nowhere.md" not in result.stdout


def test_prose_lint_flags_rules_outside_code_and_tables(tmp_path: Path) -> None:
    long_sentence = " ".join(["word"] * 30) + "."
    (tmp_path / "doc.md").write_text(
        "# Title\n\n"
        "You should run it; it's easy.\n\n"
        f"- {long_sentence}\n"
        "- Short item.\n\n"
        "| should | may |\n| --- | --- |\n\n"
        "```text\nyou should not flag code; ever\n```\n",
        encoding="utf-8",
    )
    result = run(["python3", str(PROSE_LINT), "doc.md"], tmp_path)
    assert result.returncode == 0
    assert "modal: 'should'" in result.stdout
    assert "semicolon" in result.stdout
    assert "contraction" in result.stdout
    assert "long-sentence: 30 words" in result.stdout
    assert "ever" not in result.stdout
    strict = run(["python3", str(PROSE_LINT), "--strict", "doc.md"], tmp_path)
    assert strict.returncode == 1


def test_prose_lint_passes_plain_text(tmp_path: Path) -> None:
    (tmp_path / "doc.md").write_text(
        "# Title\n\nRun the check. It takes one minute.\n", encoding="utf-8"
    )
    result = run(["python3", str(PROSE_LINT), "--strict", "doc.md"], tmp_path)
    assert result.returncode == 0, result.stdout
    assert "0 findings" in result.stdout


def test_render_mermaid_extracts_each_block(tmp_path: Path) -> None:
    (tmp_path / "doc.md").write_text(
        "# Doc\n\n```mermaid\nflowchart LR\n  A --> B\n```\n\ntext\n\n"
        "```mermaid\nsequenceDiagram\n  A->>B: hi\n```\n",
        encoding="utf-8",
    )
    out = tmp_path / "out"
    result = run(
        ["bash", str(RENDER_MERMAID), "--extract", "--out", str(out), "doc.md"],
        tmp_path,
    )
    assert result.returncode == 0, result.stdout
    assert sorted(p.name for p in out.glob("*.mmd")) == ["doc-1.mmd", "doc-2.mmd"]
    assert (out / "doc-2.mmd").read_text(encoding="utf-8").startswith("sequenceDiagram")


def test_render_mermaid_reports_missing_mmdc(tmp_path: Path) -> None:
    (tmp_path / "doc.md").write_text(
        "```mermaid\nflowchart LR\n  A --> B\n```\n", encoding="utf-8"
    )
    env = {**os.environ, "PATH": "/usr/bin:/bin"}
    result = run(["bash", str(RENDER_MERMAID), "doc.md"], tmp_path, env=env)
    assert result.returncode == 2
    assert "mmdc not found" in result.stdout
