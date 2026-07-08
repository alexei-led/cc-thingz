"""Tests for the plugin composition index and output-path resolver (Task 11).

Covers:
- Reading multiple `plugin.yaml` files into the per-kind reverse index.
- Real repo `src/plugins/*/plugin.yaml` parses cleanly.
- `output_paths` behavior for plugin-grouped vs flat targets, with one /
  many / zero owning plugins.
"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def pi_mod(load_script):
    return load_script("build/plugin_index.py")


@pytest.fixture
def fake_plugins_root(tmp_path: Path) -> Path:
    """Create a `<tmp>/src/plugins/` tree with three minimal plugins."""
    root = tmp_path
    plugins = root / "src" / "plugins"
    plugins.mkdir(parents=True)

    (plugins / "alpha").mkdir()
    (plugins / "alpha" / "plugin.yaml").write_text(
        "name: alpha\n"
        "version: 1.0.0\n"
        "description: Alpha plugin\n"
        "skills:\n"
        "  - shared-skill\n"
        "  - only-alpha\n"
        "agents:\n"
        "  - only-alpha-agent\n"
        "hooks:\n"
        "  - shared-hook\n"
    )

    (plugins / "beta").mkdir()
    (plugins / "beta" / "plugin.yaml").write_text(
        "name: beta\n"
        "version: 1.0.0\n"
        "description: Beta plugin\n"
        "skills:\n"
        "  - shared-skill\n"
        "  - only-beta\n"
        "agents: []\n"
        "hooks:\n"
        "  - shared-hook\n"
        "  - only-beta-hook\n"
    )

    # plugin with no plugin.yaml — must be silently ignored
    (plugins / "skipme").mkdir()

    return root


def test_build_plugin_index_real_repo(pi_mod):
    """The shipped src/plugins/*.yaml files load and contain expected wiring."""
    repo_root = Path(__file__).resolve().parent.parent
    index = pi_mod.build_plugin_index(repo_root)

    # All three kinds present.
    assert set(index) == {"skills", "agents", "hooks"}

    # committing-code belongs to dev-flow.
    assert index["skills"]["committing-code"] == ["dev-flow"]
    # git hygiene skills belong to git-flow.
    assert index["skills"]["configuring-git-hygiene"] == ["git-flow"]
    assert "configuring-git-flow" not in index["skills"]
    # engineer is a shared role agent; dev-flow is one of its owners.
    assert "dev-flow" in index["agents"]["engineer"]
    # session-start hook belongs to dev-flow.
    assert index["hooks"]["session-start"] == ["dev-flow"]


def test_build_plugin_index_reverse_mapping(pi_mod, fake_plugins_root):
    index = pi_mod.build_plugin_index(fake_plugins_root)
    assert index["skills"]["shared-skill"] == ["alpha", "beta"]
    assert index["skills"]["only-alpha"] == ["alpha"]
    assert index["skills"]["only-beta"] == ["beta"]
    assert index["agents"]["only-alpha-agent"] == ["alpha"]
    assert index["hooks"]["shared-hook"] == ["alpha", "beta"]
    assert index["hooks"]["only-beta-hook"] == ["beta"]


def test_build_plugin_index_ignores_dirs_without_manifest(pi_mod, fake_plugins_root):
    index = pi_mod.build_plugin_index(fake_plugins_root)
    for kind in ("skills", "agents", "hooks"):
        for owners in index[kind].values():
            assert "skipme" not in owners


def test_build_plugin_index_empty_when_no_plugins_dir(pi_mod, tmp_path):
    index = pi_mod.build_plugin_index(tmp_path)
    assert index == {"skills": {}, "agents": {}, "hooks": {}}


def test_build_plugin_index_invalid_yaml_raises(pi_mod, tmp_path):
    bad = tmp_path / "src" / "plugins" / "bad"
    bad.mkdir(parents=True)
    (bad / "plugin.yaml").write_text("name: bad\nskills: : :\n")
    with pytest.raises(ValueError, match="invalid YAML"):
        pi_mod.build_plugin_index(tmp_path)


def test_build_plugin_index_rejects_non_list_kind(pi_mod, tmp_path):
    bad = tmp_path / "src" / "plugins" / "bad"
    bad.mkdir(parents=True)
    (bad / "plugin.yaml").write_text("name: bad\nskills:\n  not: list\n")
    with pytest.raises(ValueError, match="must be a list"):
        pi_mod.build_plugin_index(tmp_path)


def test_build_plugin_index_rejects_non_string_entry(pi_mod, tmp_path):
    bad = tmp_path / "src" / "plugins" / "bad"
    bad.mkdir(parents=True)
    (bad / "plugin.yaml").write_text("name: bad\nskills:\n  - 42\n")
    with pytest.raises(ValueError, match="must be strings"):
        pi_mod.build_plugin_index(tmp_path)


def test_build_plugin_index_rejects_unsafe_name(pi_mod, tmp_path):
    bad = tmp_path / "src" / "plugins" / "bad"
    bad.mkdir(parents=True)
    (bad / "plugin.yaml").write_text("name: ../evil\nskills:\n  - s\n")
    with pytest.raises(ValueError, match="unsafe characters"):
        pi_mod.build_plugin_index(tmp_path)


def test_owners_returns_empty_for_unknown(pi_mod, fake_plugins_root):
    index = pi_mod.build_plugin_index(fake_plugins_root)
    assert pi_mod.owners("nope", "skills", index) == []
    assert pi_mod.owners("shared-skill", "skills", None) == []


def test_owners_rejects_bad_kind(pi_mod):
    with pytest.raises(ValueError, match="unknown kind"):
        pi_mod.owners("x", "bogus", {})


def test_output_paths_plugin_grouped_single_owner(pi_mod, fake_plugins_root):
    index = pi_mod.build_plugin_index(fake_plugins_root)
    paths = pi_mod.output_paths(
        "only-alpha", "skills", "claude", index, fake_plugins_root
    )
    assert paths == [fake_plugins_root / "dist/claude/plugins/alpha/skills"]


def test_output_paths_plugin_grouped_many_owners(pi_mod, fake_plugins_root):
    index = pi_mod.build_plugin_index(fake_plugins_root)
    paths = pi_mod.output_paths(
        "shared-skill", "skills", "codex", index, fake_plugins_root
    )
    assert paths == [
        fake_plugins_root / "dist/codex/plugins/alpha/skills",
        fake_plugins_root / "dist/codex/plugins/beta/skills",
    ]


def test_output_paths_plugin_grouped_no_owner_returns_empty(pi_mod, fake_plugins_root):
    index = pi_mod.build_plugin_index(fake_plugins_root)
    assert (
        pi_mod.output_paths("orphan", "skills", "claude", index, fake_plugins_root)
        == []
    )
    # Codex agents land flat regardless of plugin ownership (agent_layout=flat).
    assert pi_mod.output_paths(
        "orphan", "agents", "codex", index, fake_plugins_root
    ) == [fake_plugins_root / "dist/codex/agents"]
    # Claude agents still require plugin ownership.
    assert (
        pi_mod.output_paths("orphan", "agents", "claude", index, fake_plugins_root)
        == []
    )


def test_output_paths_flat_target_ignores_plugin_index(pi_mod, fake_plugins_root):
    index = pi_mod.build_plugin_index(fake_plugins_root)
    # Owned artifact: still single flat path.
    assert pi_mod.output_paths(
        "shared-skill", "skills", "pi", index, fake_plugins_root
    ) == [fake_plugins_root / "dist/pi/skills"]
    # Orphan artifact: still emitted flat for Pi.
    assert pi_mod.output_paths("orphan", "skills", "pi", index, fake_plugins_root) == [
        fake_plugins_root / "dist/pi/skills"
    ]
    # Same for Gemini (also flat).
    assert pi_mod.output_paths(
        "orphan", "skills", "gemini", index, fake_plugins_root
    ) == [fake_plugins_root / "dist/gemini/skills"]


def test_output_paths_uses_kind_specific_leaf(pi_mod, fake_plugins_root):
    index = pi_mod.build_plugin_index(fake_plugins_root)
    skill_paths = pi_mod.output_paths(
        "only-alpha", "skills", "claude", index, fake_plugins_root
    )
    agent_paths = pi_mod.output_paths(
        "only-alpha-agent", "agents", "claude", index, fake_plugins_root
    )
    hook_paths = pi_mod.output_paths(
        "shared-hook", "hooks", "claude", index, fake_plugins_root
    )
    assert skill_paths[0].name == "skills"
    assert agent_paths[0].name == "agents"
    assert hook_paths[0].name == "hooks"


def test_output_paths_rejects_unknown_target(pi_mod, fake_plugins_root):
    with pytest.raises(ValueError, match="unknown target"):
        pi_mod.output_paths("x", "skills", "bogus", {}, fake_plugins_root)


def test_output_paths_rejects_unknown_kind(pi_mod, fake_plugins_root):
    with pytest.raises(ValueError, match="unknown kind"):
        pi_mod.output_paths("x", "bogus", "claude", {}, fake_plugins_root)


def test_output_paths_none_index_treated_as_empty(pi_mod, fake_plugins_root):
    # No plugin index = no owners = no plugin-grouped paths.
    assert (
        pi_mod.output_paths("shared-skill", "skills", "claude", None, fake_plugins_root)
        == []
    )
    # Flat targets still emit.
    assert pi_mod.output_paths(
        "shared-skill", "skills", "pi", None, fake_plugins_root
    ) == [fake_plugins_root / "dist/pi/skills"]


def _write_skill(root: Path, name: str, frontmatter_block: str = "") -> None:
    skill_dir = root / "src" / "skills" / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: d\n{frontmatter_block}---\n\nbody\n"
    )


def _write_agent(root: Path, name: str, frontmatter_block: str = "") -> None:
    agent_dir = root / "src" / "agents" / name
    agent_dir.mkdir(parents=True, exist_ok=True)
    (agent_dir / "AGENT.md").write_text(
        f"---\nname: {name}\ndescription: d\n{frontmatter_block}---\n\nbody\n"
    )


def test_validate_plugin_ownership_passes_when_all_owned(pi_mod, fake_plugins_root):
    _write_skill(fake_plugins_root, "shared-skill")
    _write_skill(fake_plugins_root, "only-alpha")
    _write_skill(fake_plugins_root, "only-beta")
    _write_agent(fake_plugins_root, "only-alpha-agent")
    index = pi_mod.build_plugin_index(fake_plugins_root)
    pi_mod.validate_plugin_ownership(fake_plugins_root, index)


def test_validate_plugin_ownership_fails_on_orphan_skill(pi_mod, fake_plugins_root):
    _write_skill(fake_plugins_root, "shared-skill")
    _write_skill(fake_plugins_root, "only-alpha")
    _write_skill(fake_plugins_root, "only-beta")
    _write_skill(fake_plugins_root, "lonely")  # not in any plugin.yaml
    index = pi_mod.build_plugin_index(fake_plugins_root)
    with pytest.raises(ValueError, match="not owned by any plugin"):
        pi_mod.validate_plugin_ownership(fake_plugins_root, index)


def test_validate_plugin_ownership_allows_pi_only_orphan(pi_mod, fake_plugins_root):
    _write_skill(fake_plugins_root, "shared-skill")
    _write_skill(fake_plugins_root, "only-alpha")
    _write_skill(fake_plugins_root, "only-beta")
    _write_agent(fake_plugins_root, "only-alpha-agent")
    _write_agent(fake_plugins_root, "pi-only-orphan", "targets:\n  - pi\n")
    index = pi_mod.build_plugin_index(fake_plugins_root)
    pi_mod.validate_plugin_ownership(fake_plugins_root, index)


def test_validate_plugin_ownership_allows_gemini_only_orphan(pi_mod, fake_plugins_root):
    _write_skill(fake_plugins_root, "shared-skill")
    _write_skill(fake_plugins_root, "only-alpha")
    _write_skill(fake_plugins_root, "only-beta")
    _write_agent(fake_plugins_root, "only-alpha-agent")
    _write_skill(fake_plugins_root, "gemini-only", "targets:\n  - pi\n  - gemini\n")
    index = pi_mod.build_plugin_index(fake_plugins_root)
    pi_mod.validate_plugin_ownership(fake_plugins_root, index)


def test_validate_plugin_ownership_fails_on_claude_only_orphan(
    pi_mod, fake_plugins_root
):
    _write_skill(fake_plugins_root, "shared-skill")
    _write_skill(fake_plugins_root, "only-alpha")
    _write_skill(fake_plugins_root, "only-beta")
    _write_agent(fake_plugins_root, "only-alpha-agent")
    # Claude-only orphan is still wrong: the build would emit nothing for it.
    _write_skill(fake_plugins_root, "claude-orphan", "targets:\n  - claude\n")
    index = pi_mod.build_plugin_index(fake_plugins_root)
    with pytest.raises(ValueError, match="claude-orphan"):
        pi_mod.validate_plugin_ownership(fake_plugins_root, index)
