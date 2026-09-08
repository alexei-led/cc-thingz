from __future__ import annotations

import json

import pytest
from conftest import _load

prepare_skill_evals = _load("prepare-skill-evals.py")


@pytest.fixture
def project(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    root.mkdir()
    monkeypatch.setattr(prepare_skill_evals, "ROOT", root)
    monkeypatch.setattr(prepare_skill_evals, "DIST_DIR", root / "dist")
    monkeypatch.setattr(prepare_skill_evals, "EVALS_DIR", root / "tests/skill-evals")
    skill = root / "dist/claude/programming/skills/writing-shell"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("compiled skill", encoding="utf-8")
    suite = root / "tests/skill-evals/programming/writing-shell/evals"
    suite.mkdir(parents=True)
    (suite / "evals.json").write_text(
        json.dumps(
            {
                "skill_name": "writing-shell",
                "evals": [
                    {
                        "id": "shell",
                        "prompt": "describe workflow",
                        "assertions": ["checks"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return root


def test_cli_prepares_and_reuses_owned_output(project, tmp_path, capsys):
    out = tmp_path / "out"
    assert prepare_skill_evals.main(["--out", str(out)]) == 0
    dest = out / "programming/skills/writing-shell"
    assert (dest / "SKILL.md").read_text() == "compiled skill"
    assert (dest / "evals/evals.json").is_file()
    assert "from claude" in capsys.readouterr().out
    assert prepare_skill_evals.main(["--out", str(out)]) == 0
    assert json.loads((out / "inventory.json").read_text())["evals"] == 1


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
            (out / prepare_skill_evals.MARKER).write_text("{}")
    assert prepare_skill_evals.main(["--out", str(out)]) == 1
    assert "ERROR:" in capsys.readouterr().err
    assert sentinel.read_text() == "keep"
    assert (project / "dist/claude/programming/skills/writing-shell/SKILL.md").is_file()
    if which in {"existing", "bad-marker"}:
        assert (out / "user-file").read_text() == "keep"


def test_missing_compiled_skill_fails_before_touching_output(project, tmp_path, capsys):
    out = tmp_path / "out"
    assert prepare_skill_evals.main(["--out", str(out)]) == 0
    skill = project / "dist/claude/programming/skills/writing-shell/SKILL.md"
    skill.unlink()
    assert prepare_skill_evals.main(["--out", str(out)]) == 1
    assert "no compiled claude skill" in capsys.readouterr().err
    assert (out / "programming/skills/writing-shell/SKILL.md").is_file()


def test_inventory_reports_uncovered_without_writes(project, capsys):
    uncovered = project / "dist/claude/programming/skills/writing-python"
    uncovered.mkdir()
    (uncovered / "SKILL.md").write_text("python")
    assert prepare_skill_evals.main(["--inventory"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["uncovered_skills"] == ["programming/writing-python"]
    assert report["active"] == [{"skill": "programming/writing-shell", "evals": 1}]


def test_unregistered_archive_is_error(project):
    archive = project / "tests/skill-evals/archive/old/retired/evals"
    archive.mkdir(parents=True)
    (archive / "evals.json").write_text("{}")
    with pytest.raises(prepare_skill_evals.EvalPrepError, match="exactly match"):
        prepare_skill_evals.inventory()


def test_repository_inventory_accounts_for_all_original_scenarios():
    report = prepare_skill_evals.inventory()
    assert report["skills"] == 25
    assert report["evals"] == 72
    assert sum(entry["evals"] for entry in report["archived"]) == 2
    assert report["uncovered_skills"] == [
        "discovery/installation-doctor",
        "git-flow/cleanup-git",
        "programming/writing-csharp",
        "programming/writing-java-kotlin",
        "spec-flow/spec-flow",
    ]
    assert report == prepare_skill_evals.inventory()


@pytest.mark.parametrize(
    "location", ["notes.txt", "programming/skills/writing-shell/notes.txt"]
)
def test_owned_output_preserves_unexpected_files(project, tmp_path, location, capsys):
    out = tmp_path / "out"
    assert prepare_skill_evals.main(["--out", str(out)]) == 0
    extra = out / location
    extra.write_text("keep")
    assert prepare_skill_evals.main(["--out", str(out)]) == 1
    assert "unexpected or missing entries" in capsys.readouterr().err
    assert extra.read_text() == "keep"
