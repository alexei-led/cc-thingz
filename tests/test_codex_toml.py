"""Tests for `scripts/build/codex_toml.py`.

Each test renders an `agent_meta + body` pair through `to_toml`, then parses
the output with stdlib `tomllib` and asserts the parsed structure rather than
relying on exact string formatting. The triple-quote escape test additionally
checks the raw output to verify the closing delimiter is unambiguous.
"""

from __future__ import annotations

import tomllib

import pytest


def _to_toml(load_script):
    mod = load_script("codex_toml.py")
    return mod.to_toml


def test_minimal_agent_emits_name_description_and_body(load_script):
    to_toml = _to_toml(load_script)
    out = to_toml(
        {"name": "go-engineer", "description": "Go specialist."},
        "You are a Go engineer.\n",
    )
    data = tomllib.loads(out)
    assert data["name"] == "go-engineer"
    assert data["description"] == "Go specialist."
    assert "You are a Go engineer." in data["developer_instructions"]


def test_effort_renames_to_model_reasoning_effort(load_script):
    to_toml = _to_toml(load_script)
    out = to_toml(
        {"name": "a", "description": "d", "model": "sonnet", "effort": "high"},
        "body\n",
    )
    data = tomllib.loads(out)
    assert data["model"] == "sonnet"
    assert data["model_reasoning_effort"] == "high"
    assert "effort" not in data


def test_explicit_model_reasoning_effort_wins_over_effort(load_script):
    to_toml = _to_toml(load_script)
    out = to_toml(
        {
            "name": "a",
            "description": "d",
            "effort": "low",
            "model_reasoning_effort": "high",
        },
        "body\n",
    )
    data = tomllib.loads(out)
    assert data["model_reasoning_effort"] == "high"
    assert "effort" not in data


def test_none_scalar_values_are_omitted(load_script):
    """`field: null` in YAML must not emit `field = "None"` in TOML."""
    to_toml = _to_toml(load_script)
    out = to_toml(
        {
            "name": "a",
            "description": None,
            "model": None,
            "sandbox_mode": "workspace-write",
        },
        "body\n",
    )
    data = tomllib.loads(out)
    assert "description" not in data
    assert "model" not in data
    assert data["sandbox_mode"] == "workspace-write"
    assert 'description = "None"' not in out
    assert 'model = "None"' not in out


def test_nickname_candidates_pass_through_as_string_array(load_script):
    to_toml = _to_toml(load_script)
    out = to_toml(
        {
            "name": "a",
            "description": "d",
            "nickname_candidates": ["alpha", "beta", "gamma"],
        },
        "body\n",
    )
    data = tomllib.loads(out)
    assert data["nickname_candidates"] == ["alpha", "beta", "gamma"]


def test_sandbox_mode_passes_through(load_script):
    to_toml = _to_toml(load_script)
    out = to_toml(
        {"name": "a", "description": "d", "sandbox_mode": "workspace-write"},
        "body\n",
    )
    data = tomllib.loads(out)
    assert data["sandbox_mode"] == "workspace-write"


def test_mcp_servers_become_dotted_tables(load_script):
    to_toml = _to_toml(load_script)
    out = to_toml(
        {
            "name": "a",
            "description": "d",
            "mcp_servers": {
                "github": {"command": "uvx", "args": ["github-mcp"]},
                "fs": {"command": "node", "args": ["fs.js"], "env": {"DEBUG": "1"}},
            },
        },
        "body\n",
    )
    data = tomllib.loads(out)
    assert data["mcp_servers"]["github"] == {
        "command": "uvx",
        "args": ["github-mcp"],
    }
    assert data["mcp_servers"]["fs"]["command"] == "node"
    assert data["mcp_servers"]["fs"]["env"] == {"DEBUG": "1"}


def test_skills_config_emits_array_of_tables(load_script):
    to_toml = _to_toml(load_script)
    out = to_toml(
        {
            "name": "a",
            "description": "d",
            "skills": {
                "config": [
                    {"name": "writing-go", "enabled": True},
                    {"name": "looking-up-docs"},
                ],
            },
        },
        "body\n",
    )
    data = tomllib.loads(out)
    config = data["skills"]["config"]
    assert config[0] == {"name": "writing-go", "enabled": True}
    assert config[1] == {"name": "looking-up-docs"}


def test_skills_bare_list_of_strings_lifts_to_config_entries(load_script):
    to_toml = _to_toml(load_script)
    out = to_toml(
        {
            "name": "a",
            "description": "d",
            "skills": ["writing-go", "coding"],
        },
        "body\n",
    )
    data = tomllib.loads(out)
    assert data["skills"]["config"] == [
        {"name": "writing-go"},
        {"name": "coding"},
    ]


def test_body_containing_triple_quotes_is_escaped(load_script):
    to_toml = _to_toml(load_script)
    body = 'before """triple""" after\n'
    out = to_toml({"name": "a", "description": "d"}, body)
    # No raw triple-quote sequence anywhere except the opening/closing pair.
    triple_count = out.count('"""')
    assert triple_count == 2, f"unexpected number of triple-quotes: {triple_count}"
    data = tomllib.loads(out)
    # Round-trip preserves the original characters.
    assert 'before """triple""" after' in data["developer_instructions"]


def test_backslash_in_body_is_doubled(load_script):
    to_toml = _to_toml(load_script)
    body = "path C:\\foo\\bar\n"
    out = to_toml({"name": "a", "description": "d"}, body)
    data = tomllib.loads(out)
    assert "C:\\foo\\bar" in data["developer_instructions"]


def test_description_special_chars_are_escaped(load_script):
    to_toml = _to_toml(load_script)
    out = to_toml(
        {"name": "a", "description": 'Has "quotes" and\nnewlines.'},
        "body\n",
    )
    data = tomllib.loads(out)
    assert data["description"] == 'Has "quotes" and\nnewlines.'


def test_unknown_mcp_servers_shape_raises(load_script):
    to_toml = _to_toml(load_script)
    with pytest.raises(ValueError, match="mcp_servers"):
        to_toml(
            {"name": "a", "description": "d", "mcp_servers": ["not", "a", "mapping"]},
            "body\n",
        )


def test_output_key_order_is_stable(load_script):
    to_toml = _to_toml(load_script)
    out = to_toml(
        {
            "description": "d",
            "name": "a",
            "model": "sonnet",
            "sandbox_mode": "ws",
            "model_reasoning_effort": "high",
            "nickname_candidates": ["x"],
        },
        "body\n",
    )
    lines = out.splitlines()
    # name first, description second, then scalars in fixed order, then
    # nickname_candidates, then developer_instructions.
    assert lines[0].startswith("name = ")
    assert lines[1].startswith("description = ")
    assert lines[2].startswith("model = ")
    assert lines[3].startswith("model_reasoning_effort = ")
    assert lines[4].startswith("sandbox_mode = ")
    assert lines[5].startswith("nickname_candidates = ")
    assert 'developer_instructions = """' in out


def test_full_agent_round_trips_through_tomllib(load_script):
    to_toml = _to_toml(load_script)
    meta = {
        "name": "go-engineer",
        "description": "Go development specialist.",
        "model": "sonnet",
        "effort": "high",
        "sandbox_mode": "workspace-write",
        "nickname_candidates": ["go-dev", "gopher"],
        "mcp_servers": {
            "search": {"command": "uvx", "args": ["search-mcp"]},
        },
        "skills": {
            "config": [{"name": "writing-go"}, {"name": "smart-explore"}],
        },
    }
    body = "# Go Engineer\n\nYou design and review idiomatic Go.\n"
    out = to_toml(meta, body)
    data = tomllib.loads(out)
    assert data["name"] == "go-engineer"
    assert data["description"] == "Go development specialist."
    assert data["model"] == "sonnet"
    assert data["model_reasoning_effort"] == "high"
    assert data["sandbox_mode"] == "workspace-write"
    assert data["nickname_candidates"] == ["go-dev", "gopher"]
    assert data["mcp_servers"]["search"] == {
        "command": "uvx",
        "args": ["search-mcp"],
    }
    assert data["skills"]["config"] == [
        {"name": "writing-go"},
        {"name": "smart-explore"},
    ]
    assert "Go Engineer" in data["developer_instructions"]
