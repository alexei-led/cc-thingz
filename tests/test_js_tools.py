from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

from conftest import REPO_ROOT

SCRIPT = REPO_ROOT / "scripts" / "tooling" / "js-tools.sh"


def fake_tool(directory: Path, name: str) -> None:
    path = directory / name
    path.write_text(f'#!/usr/bin/env bash\nprintf \'%s\\n\' "$*" >"$PWD/{name}.args"\n')
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def run_tool(repo: Path, mode: str, bin_dir: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:/usr/bin:/bin"
    return subprocess.run(
        [str(SCRIPT), mode],
        cwd=repo,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def test_prefers_oxfmt_for_formatting_when_available(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "package.json").write_text("{}\n")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake_tool(bin_dir, "oxfmt")
    fake_tool(bin_dir, "biome")
    fake_tool(bin_dir, "oxlint")

    formatted = run_tool(tmp_path, "format", bin_dir)
    linted = run_tool(tmp_path, "lint", bin_dir)

    assert formatted.returncode == 0, formatted.stdout
    assert linted.returncode == 0, linted.stdout
    assert (tmp_path / "oxfmt.args").read_text() == "--write src tests\n"
    assert (tmp_path / "oxlint.args").read_text() == "src tests\n"
    assert not (tmp_path / "biome.args").exists()


def test_uses_fast_tools_when_project_has_no_tool_choice(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "package.json").write_text("{}\n")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake_tool(bin_dir, "biome")
    fake_tool(bin_dir, "oxlint")

    formatted = run_tool(tmp_path, "format", bin_dir)
    linted = run_tool(tmp_path, "lint", bin_dir)

    assert formatted.returncode == 0, formatted.stdout
    assert linted.returncode == 0, linted.stdout
    assert (tmp_path / "biome.args").read_text() == "format --write src tests\n"
    assert (tmp_path / "oxlint.args").read_text() == "src tests\n"


def test_project_formatter_and_linter_win_over_machine_defaults(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / ".prettierrc").write_text("{}\n")
    (tmp_path / "eslint.config.js").write_text("export default [];\n")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for tool in ("biome", "oxlint", "prettier", "eslint"):
        fake_tool(bin_dir, tool)

    formatted = run_tool(tmp_path, "format", bin_dir)
    linted = run_tool(tmp_path, "lint", bin_dir)

    assert formatted.returncode == 0, formatted.stdout
    assert linted.returncode == 0, linted.stdout
    assert "src/**/*.ts" in (tmp_path / "prettier.args").read_text()
    assert (
        "--cache --no-error-on-unmatched-pattern"
        in (tmp_path / "eslint.args").read_text()
    )
    assert not (tmp_path / "biome.args").exists()
    assert not (tmp_path / "oxlint.args").exists()
