from __future__ import annotations

import json

import pytest
from conftest import _load

prepare_plugin_evals = _load("prepare-plugin-evals.py")


@pytest.fixture
def project(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    root.mkdir()
    monkeypatch.setattr(prepare_plugin_evals, "ROOT", root)
    monkeypatch.setattr(prepare_plugin_evals, "DIST_DIR", root / "dist")
    monkeypatch.setattr(
        prepare_plugin_evals, "FIXTURES_DIR", root / "tests/plugin-evals"
    )
    plugin = root / "dist/claude/git-flow"
    skill = plugin / "skills/using-git-worktrees"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("compiled skill", encoding="utf-8")
    (plugin / "README.md").write_text("plugin readme", encoding="utf-8")
    case = root / "tests/plugin-evals/git-flow/using-git-worktrees/evals/smoke"
    (case / "graders").mkdir(parents=True)
    (case / "prompt.md").write_text("do the thing", encoding="utf-8")
    (case / "graders" / "criteria.md").write_text("check the thing", encoding="utf-8")
    return root


def test_cli_prepares_plugin_copy_with_evals(project, tmp_path, capsys):
    out = tmp_path / "out"
    assert prepare_plugin_evals.main(["--package", "git-flow", "--out", str(out)]) == 0
    assert (out / "README.md").read_text() == "plugin readme"
    assert (out / "skills/using-git-worktrees/SKILL.md").read_text() == "compiled skill"
    assert (out / "evals/using-git-worktrees/smoke/prompt.md").read_text() == (
        "do the thing"
    )
    assert (
        out / "evals/using-git-worktrees/smoke/graders/criteria.md"
    ).read_text() == "check the thing"
    assert "prepared 1 skill(s), 1 case(s) for git-flow" in capsys.readouterr().out
    inventory = json.loads((out / "inventory.json").read_text())
    assert inventory["cases"] == 1
    # rerun reuses the owned output without complaint
    assert prepare_plugin_evals.main(["--package", "git-flow", "--out", str(out)]) == 0


def test_inventory_without_package(project, capsys):
    assert prepare_plugin_evals.main(["--inventory"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report == {
        "source_target": "claude",
        "active": [
            {"skill": "git-flow/using-git-worktrees", "cases": ["smoke"]},
        ],
        "packages": ["git-flow"],
        "skills": 1,
        "cases": 1,
    }


def test_missing_package_argument_is_error(project, capsys):
    assert prepare_plugin_evals.main([]) == 1
    assert "--package is required" in capsys.readouterr().err


def test_missing_compiled_package_is_error(project, tmp_path, capsys):
    assert (
        prepare_plugin_evals.main(
            ["--package", "dev-flow", "--out", str(tmp_path / "out")]
        )
        == 1
    )
    assert "no compiled claude package: dev-flow" in capsys.readouterr().err


def test_package_without_fixtures_is_error(project, tmp_path, capsys):
    other = project / "dist/claude/dev-flow/skills/reviewing-code"
    other.mkdir(parents=True)
    (other / "SKILL.md").write_text("compiled", encoding="utf-8")
    assert (
        prepare_plugin_evals.main(
            ["--package", "dev-flow", "--out", str(tmp_path / "out")]
        )
        == 1
    )
    assert "no plugin eval fixtures found for package: dev-flow" in (
        capsys.readouterr().err
    )


def test_invalid_case_missing_grader_fails_fast(project, tmp_path):
    case = project / "tests/plugin-evals/git-flow/using-git-worktrees/evals/broken"
    case.mkdir()
    (case / "prompt.md").write_text("no graders here", encoding="utf-8")
    with pytest.raises(
        prepare_plugin_evals.PluginEvalPrepError, match="invalid eval case"
    ):
        prepare_plugin_evals.inventory()


@pytest.mark.parametrize(
    "which", ["repository", "nested", "ancestor", "existing", "symlink", "bad-marker"]
)
def test_cli_rejects_unsafe_output_without_deletion(project, tmp_path, which, capsys):
    sentinel = tmp_path / "sentinel"
    sentinel.write_text("keep")
    out = tmp_path / "out"
    if which == "repository":
        out = project
    elif which == "nested":
        out = project / "scratch"
    elif which == "ancestor":
        out = tmp_path
    elif which == "symlink":
        out.symlink_to(project, target_is_directory=True)
    else:
        out.mkdir()
        (out / "user-file").write_text("keep")
        if which == "bad-marker":
            (out / prepare_plugin_evals.MARKER).write_text("{}")
    assert prepare_plugin_evals.main(["--package", "git-flow", "--out", str(out)]) == 1
    assert "ERROR:" in capsys.readouterr().err
    assert sentinel.read_text() == "keep"
    assert (
        project / "dist/claude/git-flow/skills/using-git-worktrees/SKILL.md"
    ).is_file()
    if which in {"existing", "bad-marker"}:
        assert (out / "user-file").read_text() == "keep"


def test_case_yaml_only_case_needs_no_graders_dir(project, tmp_path):
    case = project / "tests/plugin-evals/git-flow/using-git-worktrees/evals/yaml-case"
    case.mkdir()
    (case / "case.yaml").write_text("schema_version: '1.0'", encoding="utf-8")
    report = prepare_plugin_evals.inventory()
    entry = next(
        e for e in report["active"] if e["skill"] == "git-flow/using-git-worktrees"
    )
    assert set(entry["cases"]) == {"smoke", "yaml-case"}


def test_repository_inventory_covers_the_pilot_skill():
    report = prepare_plugin_evals.inventory()
    assert report["packages"] == ["git-flow"]
    assert {e["skill"] for e in report["active"]} == {"git-flow/using-git-worktrees"}
    worktrees = next(iter(report["active"]))
    assert set(worktrees["cases"]) == {
        "create-parallel-dirty-main",
        "cleanup-after-merge-no-gh",
        "conflict-branch-checked-out-elsewhere",
        "simple-branch-switch-no-worktree",
    }
