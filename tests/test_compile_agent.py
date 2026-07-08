"""Fixture-based golden tests for `scripts.build.compile_agent.compile_agent`.

Covered cases:

- `engineer` — base + per-target frontmatter overlay (tools/model/skills),
  no body overlay. Claude and Pi are golden-locked; Codex/Gemini are
  asserted to emit one file each.
- `reviewer` — provably non-mutating envelope. Claude and Pi golden-locked;
  Bash/Edit/Write asserted absent from the compiled tools in both shapes.
- `advisor` — `targets: [pi]` restriction. Verifies only Pi receives an
  output; Claude/Codex/Gemini are skipped.

Each `(agent, target)` pair has a locked snapshot at
`tests/fixtures/golden_agents/<agent>/<target>/`. The test compiles each
agent into a tmp dist root and diffs the result against the snapshot.

Regenerating goldens: run `uv run python scripts/build/compile.py`, then
sync the relevant agent files from `dist/<target>/agents/` into
`tests/fixtures/golden_agents/<agent>/<target>/`.
"""

from __future__ import annotations

import filecmp
import tomllib
from pathlib import Path

import frontmatter
import pytest
from conftest import REPO_ROOT, make_agent_staging_root

_GOLDENS = REPO_ROOT / "tests" / "fixtures" / "golden_agents"


@pytest.fixture(scope="module")
def ca(load_script):
    """Load `compile_agent.py` via the shared loader.

    `compile.py` and `codex_toml.py` must load first so their modules are
    cached on sys.modules under their bare names — `compile_agent` imports
    them directly.
    """
    load_script("build/compile.py")
    load_script("build/codex_toml.py")
    return load_script("build/compile_agent.py")


def _norm_body(text: str) -> str:
    """Return non-blank, right-stripped lines joined with `\\n`.

    The project's markdown auto-formatter inserts or removes blank separator
    lines around sections that the compiler does not emit identically. Strip
    blank lines for the comparison.
    """
    lines = [line.rstrip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def _diff_files(golden: Path, actual: Path) -> str | None:
    """Return a diff message if files differ semantically, else None.

    `.md` files use parsed comparison (frontmatter dict + body string) so the
    test stays robust against YAML cosmetic differences introduced by the
    project's auto-formatter on the fixture files. `.toml` files use byte
    comparison since TOML is not auto-formatted in this repo.
    """
    if not actual.is_file():
        return f"missing actual file: {actual}"
    if actual.suffix == ".toml":
        if filecmp.cmp(golden, actual, shallow=False):
            return None
        # Fall back to parsed equality as a robustness net (TOML reformatting
        # is unlikely here but the message stays useful either way).
        try:
            golden_data = tomllib.loads(golden.read_text())
            actual_data = tomllib.loads(actual.read_text())
        except tomllib.TOMLDecodeError as e:
            return f"toml parse error at {actual.name}: {e}"
        if golden_data == actual_data:
            return None
        return (
            f"toml mismatch at {actual.name}\n"
            f"--- golden\n{golden.read_text(errors='replace')}\n"
            f"+++ actual\n{actual.read_text(errors='replace')}"
        )

    golden_post = frontmatter.loads(golden.read_text())
    actual_post = frontmatter.loads(actual.read_text())
    if dict(golden_post.metadata) != dict(actual_post.metadata):
        return (
            f"frontmatter mismatch at {actual.name}\n"
            f"--- golden meta\n{golden_post.metadata}\n"
            f"+++ actual meta\n{actual_post.metadata}"
        )
    if _norm_body(golden_post.content) != _norm_body(actual_post.content):
        return (
            f"body mismatch at {actual.name}\n"
            f"--- golden body\n{golden_post.content}\n"
            f"+++ actual body\n{actual_post.content}"
        )
    return None


def _compiled_tools(path: Path) -> object:
    """Return the `tools` value from a compiled agent's frontmatter.

    Pi emits a comma string; Claude and Gemini emit a YAML list. Returned
    as-is so callers can assert on the native shape.
    """
    return frontmatter.loads(path.read_text()).metadata.get("tools")


def _compiled_meta(path: Path) -> dict:
    return dict(frontmatter.loads(path.read_text()).metadata)


def test_compile_agent_engineer_all_platforms(ca, tmp_path: Path) -> None:
    """engineer has no targets restriction — every platform receives output.

    Claude and Pi carry distinct per-target frontmatter overlays
    (`claude/frontmatter.yaml`, `pi/frontmatter.yaml`) and are golden-locked.
    Codex has no overlay (base AGENT.md only); Gemini carries a
    `gemini/frontmatter.yaml` tool-allowlist overlay. Both are asserted to
    emit exactly one file so a regression that drops them is still caught.
    """
    root = make_agent_staging_root(tmp_path)
    agent_dir = root / "src" / "agents" / "engineer"
    plugin_index = {"engineer": ["dev-workflow"]}

    claude_written = ca.compile_agent(agent_dir, "claude", plugin_index, root)
    assert len(claude_written) == 1
    golden = _GOLDENS / "engineer" / "claude" / "engineer.md"
    assert golden.is_file(), f"missing golden snapshot: {golden}"
    assert _diff_files(golden, claude_written[0]) is None

    pi_written = ca.compile_agent(agent_dir, "pi", None, root)
    assert pi_written == [root / "dist" / "pi" / "agents" / "engineer.md"]
    pi_golden = _GOLDENS / "engineer" / "pi" / "engineer.md"
    assert pi_golden.is_file(), f"missing golden snapshot: {pi_golden}"
    assert _diff_files(pi_golden, pi_written[0]) is None

    assert len(ca.compile_agent(agent_dir, "codex", plugin_index, root)) == 1
    assert len(ca.compile_agent(agent_dir, "gemini", None, root)) == 1


def test_compile_agent_pi_omits_model_and_thinking(ca, tmp_path: Path) -> None:
    """Pi package agents should leave model policy to user/project settings.

    The compiled Pi agents must not emit `model` or `thinking`; otherwise
    package frontmatter would block alias-driven runtime selection and prevent
    user/project `subagents.agentOverrides` from filling those fields.
    """
    root = make_agent_staging_root(tmp_path)

    for agent_name in ("engineer", "reviewer", "runner", "advisor"):
        agent_dir = root / "src" / "agents" / agent_name
        written = ca.compile_agent(agent_dir, "pi", None, root)
        assert len(written) == 1, agent_name
        meta = _compiled_meta(written[0])
        assert "model" not in meta, (agent_name, meta)
        assert "thinking" not in meta, (agent_name, meta)


def test_compile_agent_reviewer_envelope_is_read_only(ca, tmp_path: Path) -> None:
    """reviewer's envelope must never include a mutating tool.

    Central invariant of the 39->3 consolidation, enforced per target:
    Claude and Gemini grant a hard `tools:` allowlist; Codex has no
    tool-allowlist primitive so writes are blocked via
    `sandbox_mode: read-only`; Pi relies on the system-prompt directive.
    Golden-lock Claude/Pi and assert no mutating tool leaks into the
    Claude, Pi, or Gemini tools shape.
    """
    root = make_agent_staging_root(tmp_path)
    agent_dir = root / "src" / "agents" / "reviewer"

    claude_written = ca.compile_agent(
        agent_dir, "claude", {"reviewer": ["dev-workflow"]}, root
    )
    assert len(claude_written) == 1
    claude_golden = _GOLDENS / "reviewer" / "claude" / "reviewer.md"
    assert claude_golden.is_file(), f"missing golden snapshot: {claude_golden}"
    assert _diff_files(claude_golden, claude_written[0]) is None

    pi_written = ca.compile_agent(agent_dir, "pi", None, root)
    assert pi_written == [root / "dist" / "pi" / "agents" / "reviewer.md"]
    pi_golden = _GOLDENS / "reviewer" / "pi" / "reviewer.md"
    assert pi_golden.is_file(), f"missing golden snapshot: {pi_golden}"
    assert _diff_files(pi_golden, pi_written[0]) is None

    claude_tools = _compiled_tools(claude_written[0])
    assert claude_tools == ["Read", "Grep", "Glob", "LS"], claude_tools

    pi_tools = _compiled_tools(pi_written[0])
    assert isinstance(pi_tools, str), pi_tools
    pi_tool_set = {t.strip().lower() for t in pi_tools.split(",")}
    forbidden = {"bash", "edit", "write"}
    assert pi_tool_set.isdisjoint(forbidden), (
        f"reviewer pi envelope leaked a mutating tool: {pi_tool_set & forbidden}"
    )

    gemini_written = ca.compile_agent(agent_dir, "gemini", None, root)
    assert len(gemini_written) == 1
    gemini_tools = _compiled_tools(gemini_written[0])
    assert isinstance(gemini_tools, list), gemini_tools
    gemini_forbidden = {"run_shell_command", "write_file", "replace"}
    assert not (set(gemini_tools) & gemini_forbidden), (
        f"reviewer gemini envelope leaked a mutating tool: "
        f"{set(gemini_tools) & gemini_forbidden}"
    )

    codex_written = ca.compile_agent(
        agent_dir, "codex", {"reviewer": ["dev-workflow"]}, root
    )
    assert len(codex_written) == 1
    assert codex_written[0].suffix == ".toml"
    assert 'sandbox_mode = "read-only"' in codex_written[0].read_text(), (
        "reviewer must be write-blocked on Codex (no tool-allowlist primitive)"
    )


def test_compile_agent_advisor_excludes_claude(ca, tmp_path: Path) -> None:
    """advisor has `targets: [codex, gemini, pi]`.

    Claude is excluded by design — it has a built-in advisor tool, so an
    agent definition there would be redundant. Codex/Gemini/Pi each emit
    exactly one file; the Pi output is golden-locked.
    """
    root = make_agent_staging_root(tmp_path)
    agent_dir = root / "src" / "agents" / "advisor"

    assert ca.compile_agent(agent_dir, "claude", None, root) == [], (
        "advisor must not emit for claude (built-in advisor)"
    )

    assert len(ca.compile_agent(agent_dir, "codex", None, root)) == 1
    assert len(ca.compile_agent(agent_dir, "gemini", None, root)) == 1

    written = ca.compile_agent(agent_dir, "pi", None, root)
    assert len(written) == 1
    actual = root / "dist" / "pi" / "agents" / "advisor.md"
    golden = _GOLDENS / "advisor" / "pi" / "advisor.md"

    assert golden.is_file(), f"missing golden snapshot: {golden}"
    diff = _diff_files(golden, actual)
    assert diff is None, diff

    codex_advisor = root / "dist" / "codex" / "agents" / "advisor.toml"
    assert codex_advisor.is_file()
    assert 'sandbox_mode = "read-only"' in codex_advisor.read_text(), (
        "advisor must be write-blocked on Codex (no tool-allowlist primitive)"
    )


def test_codex_target_emits_toml_extension(ca, tmp_path: Path) -> None:
    agent = tmp_path / "src" / "agents" / "tiny"
    agent.mkdir(parents=True)
    (agent / "AGENT.md").write_text(
        "---\nname: tiny\ndescription: small agent\n---\n\nbody.\n"
    )
    root = tmp_path / "repo"
    root.mkdir()
    plugin_index = {"tiny": ["alpha"]}

    written = ca.compile_agent(agent, "codex", plugin_index, root)
    assert len(written) == 1
    assert written[0].suffix == ".toml"
    text = written[0].read_text()
    assert text.startswith('name = "tiny"')
    assert 'description = "small agent"' in text
    assert "developer_instructions" in text


def test_md_targets_emit_md_extension(ca, tmp_path: Path) -> None:
    agent = tmp_path / "src" / "agents" / "tiny"
    agent.mkdir(parents=True)
    (agent / "AGENT.md").write_text(
        "---\nname: tiny\ndescription: small agent\n---\n\nbody.\n"
    )
    root = tmp_path / "repo"
    root.mkdir()
    plugin_index = {"tiny": ["alpha"]}

    for target in ("claude", "gemini", "pi"):
        written = ca.compile_agent(agent, target, plugin_index, root)
        assert len(written) == 1, target
        assert written[0].suffix == ".md", target
        text = written[0].read_text()
        assert text.startswith("---\n"), target
        assert "name: tiny" in text


def test_targets_restriction_string_form(ca, tmp_path: Path) -> None:
    agent = tmp_path / "src" / "agents" / "a"
    agent.mkdir(parents=True)
    (agent / "AGENT.md").write_text(
        "---\nname: a\ndescription: d\ntargets: pi\n---\n\nbody\n"
    )
    root = tmp_path / "repo"
    root.mkdir()
    plugin_index = {"a": ["alpha"]}

    assert ca.compile_agent(agent, "pi", plugin_index, root) != []
    assert ca.compile_agent(agent, "claude", plugin_index, root) == []


def test_targets_key_stripped_from_md_output(ca, tmp_path: Path) -> None:
    agent = tmp_path / "src" / "agents" / "a"
    agent.mkdir(parents=True)
    (agent / "AGENT.md").write_text(
        "---\nname: a\ndescription: d\ntargets:\n  - claude\n  - pi\n---\n\nbody\n"
    )
    root = tmp_path / "repo"
    root.mkdir()
    plugin_index = {"a": ["alpha"]}

    written = ca.compile_agent(agent, "claude", plugin_index, root)
    assert len(written) == 1
    assert "targets:" not in written[0].read_text()


def test_targets_key_stripped_from_toml_output(ca, tmp_path: Path) -> None:
    agent = tmp_path / "src" / "agents" / "a"
    agent.mkdir(parents=True)
    (agent / "AGENT.md").write_text(
        "---\nname: a\ndescription: d\ntargets:\n  - codex\n---\n\nbody\n"
    )
    root = tmp_path / "repo"
    root.mkdir()
    plugin_index = {"a": ["alpha"]}

    written = ca.compile_agent(agent, "codex", plugin_index, root)
    assert len(written) == 1
    assert "targets" not in written[0].read_text()


def test_name_injected_from_directory_when_missing(ca, tmp_path: Path) -> None:
    agent = tmp_path / "src" / "agents" / "from-dirname"
    agent.mkdir(parents=True)
    (agent / "AGENT.md").write_text(
        "---\ndescription: name not in frontmatter\n---\n\nbody\n"
    )
    root = tmp_path / "repo"
    root.mkdir()
    plugin_index = {"from-dirname": ["alpha"]}

    written = ca.compile_agent(agent, "claude", plugin_index, root)
    assert "name: from-dirname" in written[0].read_text()


def test_plugin_index_routes_to_plugin_dir(ca, tmp_path: Path) -> None:
    agent = tmp_path / "src" / "agents" / "my-agent"
    agent.mkdir(parents=True)
    (agent / "AGENT.md").write_text(
        "---\nname: my-agent\ndescription: routed via plugin index\n---\n\nbody\n"
    )
    root = tmp_path / "repo"
    root.mkdir()

    plugin_index = {"my-agent": ["alpha", "beta"]}
    written = ca.compile_agent(agent, "claude", plugin_index, root)
    assert len(written) == 2
    plugin_dirs = {p.parent.parent.name for p in written}
    assert plugin_dirs == {"alpha", "beta"}


def test_flat_layout_ignores_plugin_index(ca, tmp_path: Path) -> None:
    agent = tmp_path / "src" / "agents" / "my-agent"
    agent.mkdir(parents=True)
    (agent / "AGENT.md").write_text(
        "---\nname: my-agent\ndescription: flat path even with index\n---\n\nbody\n"
    )
    root = tmp_path / "repo"
    root.mkdir()

    plugin_index = {"my-agent": ["alpha"]}
    written = ca.compile_agent(agent, "pi", plugin_index, root)
    assert len(written) == 1
    assert written[0] == root / "dist" / "pi" / "agents" / "my-agent.md"


def test_body_overlay_applied_when_present(ca, tmp_path: Path) -> None:
    agent = tmp_path / "src" / "agents" / "with-overlay"
    (agent / "claude").mkdir(parents=True)
    (agent / "AGENT.md").write_text(
        "---\nname: with-overlay\ndescription: d\n---\n\n# Original\nbase body.\n"
    )
    (agent / "claude" / "body.md").write_text("# Replaced\nclaude-only body.\n")
    root = tmp_path / "repo"
    root.mkdir()
    plugin_index = {"with-overlay": ["alpha"]}

    written = ca.compile_agent(agent, "claude", plugin_index, root)
    text = written[0].read_text()
    assert "claude-only body." in text
    assert "base body." not in text


def test_plugin_grouped_target_skips_unowned_agent(ca, tmp_path: Path) -> None:
    """Unowned agents return no writes for plugin-grouped agent layouts."""
    agent = tmp_path / "src" / "agents" / "orphan"
    agent.mkdir(parents=True)
    (agent / "AGENT.md").write_text(
        "---\nname: orphan\ndescription: no owner\n---\n\nbody\n"
    )
    root = tmp_path / "repo"
    root.mkdir()

    # Claude still requires plugin ownership for agents.
    assert ca.compile_agent(agent, "claude", None, root) == []
    # Flat layouts (codex agents, pi, gemini) emit even without a plugin index.
    codex_written = ca.compile_agent(agent, "codex", None, root)
    assert codex_written == [root / "dist" / "codex" / "agents" / "orphan.toml"]
    assert ca.compile_agent(agent, "pi", None, root) != []
    assert ca.compile_agent(agent, "gemini", None, root) != []


def test_codex_agents_emit_flat_not_plugin_grouped(ca, tmp_path: Path) -> None:
    """Codex agents land at dist/codex/agents/ regardless of plugin index."""
    agent = tmp_path / "src" / "agents" / "tiny"
    agent.mkdir(parents=True)
    (agent / "AGENT.md").write_text("---\nname: tiny\ndescription: d\n---\n\nbody\n")
    root = tmp_path / "repo"
    root.mkdir()
    plugin_index = {"tiny": ["alpha", "beta"]}

    written = ca.compile_agent(agent, "codex", plugin_index, root)
    assert written == [root / "dist" / "codex" / "agents" / "tiny.toml"]
