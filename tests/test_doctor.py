from __future__ import annotations

import json
from pathlib import Path

import pytest


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


def fixture_tree(tmp_path: Path) -> tuple[Path, Path, Path]:
    repo = tmp_path / "repo"
    plugin = tmp_path / "cache/programming/1.0"
    config = tmp_path / "config"
    write_json(
        repo / "src/.agentbundler/packages/programming.json",
        {
            "id": "programming",
            "metadata": {"version": "1.0"},
            "assets": [{"path": "skills/writing-python"}],
        },
    )
    helper = repo / "src/skills/writing-python/scripts/check.py"
    helper.parent.mkdir(parents=True)
    helper.write_text("raise RuntimeError('must never execute')")
    write_json(
        plugin / ".codex-plugin/plugin.json",
        {"name": "programming", "version": "1.0"},
    )
    skill = plugin / "skills/writing-python"
    (skill / "scripts").mkdir(parents=True)
    (skill / "SKILL.md").write_text("# Python")
    (skill / "scripts/check.py").write_text(helper.read_text())
    (config / "agents").mkdir(parents=True)
    for role in ("reviewer", "runner", "advisor"):
        (config / "agents" / f"{role}.toml").write_text("not read by doctor")
    return repo, plugin, config


def snapshot(root: Path) -> dict:
    return {
        str(path.relative_to(root)): (path.read_bytes(), path.stat().st_mtime_ns)
        for path in root.rglob("*")
        if path.is_file()
    }


def test_cli_complete_resources_and_read_only(load_script, tmp_path, capsys):
    doctor = load_script("diagnostics/doctor.py")
    repo, plugin, config = fixture_tree(tmp_path)
    before = snapshot(tmp_path)
    assert (
        doctor.main(
            [
                "--repo",
                str(repo),
                "--plugin-root",
                str(plugin.parent.parent),
                "--config-root",
                str(config),
                "--json",
            ]
        )
        == 0
    )
    report = json.loads(capsys.readouterr().out)
    assert snapshot(tmp_path) == before
    assert report["schema_version"] == 1
    assert report["canonical_packages"]["programming"]["skills"] == ["writing-python"]
    assert len(report["plugins"]) == 1
    assert {c["status"] for c in report["checks"]} == {"passed", "unsupported"}
    assert all(c["command"] is None for c in report["checks"])
    assert all(c["timestamp"] and c["cwd"] == str(repo) for c in report["checks"])


def test_missing_helpers_versions_profiles_and_duplicates(load_script, tmp_path):
    doctor = load_script("diagnostics/doctor.py")
    repo, plugin, config = fixture_tree(tmp_path)
    (plugin / "skills/writing-python/scripts/check.py").unlink()
    (config / "agents/reviewer.toml").unlink()
    write_json(
        plugin / ".codex-plugin/plugin.json",
        {
            "name": "programming",
            "version": "0.9",
        },
    )
    old = tmp_path / "cache/py-dev/0.1"
    write_json(old / ".codex-plugin/plugin.json", {"name": "py-dev", "version": "0.1"})
    (old / "skills/writing-python").mkdir(parents=True)
    (old / "skills/writing-python/SKILL.md").write_text("old")
    report = doctor.inspect(repo, [tmp_path / "cache", plugin], config)
    failures = {c["check"] for c in report["checks"] if c["status"] == "failed"}
    assert failures == {
        "obsolete-package",
        "package-version",
        "skill-resources",
        "codex-agent-profile",
        "duplicate-skill",
    }
    assert len(report["plugins"]) == 2


def test_hook_duplicates_do_not_expose_or_execute_commands(load_script, tmp_path):
    doctor = load_script("diagnostics/doctor.py")
    repo, plugin, config = fixture_tree(tmp_path)
    secret = "SECRET_MARKER_NEVER_PRINT"
    group = {"matcher": "Bash", "hooks": [{"type": "command", "command": secret}]}
    write_json(plugin / "hooks/hooks.json", {"hooks": {"PreToolUse": [group, group]}})
    before = snapshot(tmp_path)
    report = doctor.inspect(repo, [plugin], config)
    assert secret not in json.dumps(report)
    assert snapshot(tmp_path) == before
    result = next(c for c in report["checks"] if c["check"] == "hook-registrations")
    assert result["status"] == "failed"
    assert "1 exact duplicate" in result["reason"]


@pytest.mark.parametrize("content", ["[]", '{"token":"secret"', "null"])
def test_bad_manifest_reports_failure_without_contents(
    load_script,
    tmp_path,
    capsys,
    content,
):
    doctor = load_script("diagnostics/doctor.py")
    repo, plugin, _ = fixture_tree(tmp_path)
    (plugin / ".codex-plugin/plugin.json").write_text(content)
    assert doctor.main(["--repo", str(repo), "--plugin-root", str(plugin)]) == 1
    output = capsys.readouterr().out
    assert "Unreadable or invalid JSON" in output
    assert "secret" not in output


def test_flat_skills_and_absent_roots_are_explicit(load_script, tmp_path):
    doctor = load_script("diagnostics/doctor.py")
    repo, plugin, _ = fixture_tree(tmp_path)
    flat = tmp_path / "skills"
    (flat / "writing-python").mkdir(parents=True)
    (flat / "writing-python/SKILL.md").write_text("local variant")
    report = doctor.inspect(repo, [plugin, tmp_path / "absent"], None, [flat])
    assert any(c["check"] == "duplicate-skill" for c in report["checks"])
    assert any(
        c["check"] == "plugin-root" and c["status"] == "skipped"
        for c in report["checks"]
    )
    assert any(
        c["check"] == "codex-agent-profile" and c["status"] == "skipped"
        for c in report["checks"]
    )


def test_target_restrictions_do_not_report_intentional_gaps(load_script, tmp_path):
    doctor = load_script("diagnostics/doctor.py")
    repo, plugin, _ = fixture_tree(tmp_path)
    manifest = repo / "src/.agentbundler/packages/programming.json"
    data = json.loads(manifest.read_text())
    data["assets"].append({"path": "skills/claude-only", "targets": ["claude"]})
    write_json(manifest, data)
    report = doctor.inspect(repo, [plugin], None)
    assert not any(c["status"] == "failed" for c in report["checks"])
    assert "claude-only" in report["canonical_packages"]["programming"]["skills"]


def test_explicit_skill_root_never_scans_home(
    load_script, tmp_path, monkeypatch, capsys
):
    doctor = load_script("diagnostics/doctor.py")
    repo, _, _ = fixture_tree(tmp_path)
    monkeypatch.setattr(Path, "home", lambda: pytest.fail("Unexpected home scan"))
    assert (
        doctor.main(["--repo", str(repo), "--skill-root", str(tmp_path), "--json"]) == 0
    )
    assert json.loads(capsys.readouterr().out)["plugins"] == []


@pytest.mark.parametrize(
    ("old_name", "replacement"),
    [
        ("dev-workflow", "dev-flow"),
        ("python-dev", "programming"),
        ("rust-dev", "programming"),
    ],
)
def test_historical_package_migrations(load_script, tmp_path, old_name, replacement):
    doctor = load_script("diagnostics/doctor.py")
    repo, plugin, _ = fixture_tree(tmp_path)
    write_json(
        plugin / ".codex-plugin/plugin.json",
        {
            "name": old_name,
            "version": "0.1",
        },
    )
    report = doctor.inspect(repo, [plugin], None)
    result = next(c for c in report["checks"] if c["check"] == "obsolete-package")
    assert result["status"] == "failed"
    assert result["reason"] == f"{old_name}: review migration to {replacement}"
