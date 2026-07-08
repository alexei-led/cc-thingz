"""Tests for `scripts.build.overlay` frontmatter merge."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def ov(load_script):
    return load_script("build/overlay.py")


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).lstrip("\n"))
    return path


def test_load_base_markdown_returns_metadata_and_body(ov, tmp_path: Path) -> None:
    src = _write(
        tmp_path / "SKILL.md",
        """
        ---
        name: foo
        description: A skill.
        ---

        # Body

        Content.
        """,
    )
    meta, body = ov.load_base(src)
    assert meta == {"name": "foo", "description": "A skill."}
    assert body.startswith("# Body")
    assert "Content." in body


def test_load_base_shell_with_comment_frontmatter(ov, tmp_path: Path) -> None:
    src = _write(
        tmp_path / "hook.sh",
        """
        #!/usr/bin/env bash
        # ---
        # event: PreToolUse
        # timeout: 30
        # ---
        echo hello
        """,
    )
    meta, body = ov.load_base(src)
    assert meta == {"event": "PreToolUse", "timeout": 30}
    assert "echo hello" in body
    assert "# ---" not in body


def test_load_base_shell_without_frontmatter(ov, tmp_path: Path) -> None:
    src = _write(tmp_path / "hook.sh", "#!/usr/bin/env bash\necho hi\n")
    meta, body = ov.load_base(src)
    assert meta == {}
    assert "echo hi" in body


def test_merge_frontmatter_base_only_when_overlay_missing(ov, tmp_path: Path) -> None:
    base = {"name": "foo", "description": "A skill."}
    merged = ov.merge_frontmatter(base, tmp_path / "missing.yaml", "claude")
    assert merged == base


def test_merge_frontmatter_overlay_adds_keys(ov, tmp_path: Path) -> None:
    base = {"name": "foo", "description": "A skill."}
    fm = _write(
        tmp_path / "frontmatter.yaml",
        """
        argument-hint: '[args]'
        user-invocable: true
        """,
    )
    merged = ov.merge_frontmatter(base, fm, "claude")
    assert merged["name"] == "foo"
    assert merged["argument-hint"] == "[args]"
    assert merged["user-invocable"] is True


def test_merge_frontmatter_overlay_replaces_scalar(ov, tmp_path: Path) -> None:
    base = {"name": "foo", "description": "Old.", "model": "sonnet"}
    fm = _write(tmp_path / "frontmatter.yaml", "model: opus\n")
    merged = ov.merge_frontmatter(base, fm, "claude")
    assert merged["model"] == "opus"
    assert merged["description"] == "Old."


def test_merge_frontmatter_overlay_replaces_list(ov, tmp_path: Path) -> None:
    base = {"name": "foo", "description": "x", "tools": ["A", "B"]}
    fm = _write(tmp_path / "frontmatter.yaml", "tools: [X, Y, Z]\n")
    merged = ov.merge_frontmatter(base, fm, "claude")
    assert merged["tools"] == ["X", "Y", "Z"]


def test_merge_frontmatter_overlay_side_wins_for_nested_dict(
    ov, tmp_path: Path
) -> None:
    base = {
        "name": "foo",
        "description": "x",
        "metadata": {"author": "a", "ver": 1},
    }
    fm = _write(
        tmp_path / "frontmatter.yaml",
        """
        metadata:
          ver: 2
          extra: "yes"
        """,
    )
    merged = ov.merge_frontmatter(base, fm, "pi")
    assert merged["metadata"] == {"author": "a", "ver": 2, "extra": "yes"}


def test_merge_frontmatter_strips_targets_key(ov) -> None:
    base = {"name": "foo", "description": "x", "targets": ["claude", "pi"]}
    merged = ov.merge_frontmatter(base, None, "claude")
    assert "targets" not in merged


def test_merge_frontmatter_filters_disallowed_keys(ov, tmp_path: Path) -> None:
    base = {"name": "foo", "description": "x"}
    fm = _write(
        tmp_path / "frontmatter.yaml",
        """
        argument-hint: '[x]'
        user-invocable: true
        """,
    )
    merged = ov.merge_frontmatter(base, fm, "codex")
    assert merged == {"name": "foo", "description": "x"}


def test_merge_frontmatter_unknown_target_raises(ov) -> None:
    with pytest.raises(ValueError, match="unknown target"):
        ov.merge_frontmatter({"name": "x"}, None, "bogus")


def test_merge_frontmatter_overlay_must_be_mapping(ov, tmp_path: Path) -> None:
    fm = _write(tmp_path / "frontmatter.yaml", "- not\n- a\n- mapping\n")
    with pytest.raises(ValueError, match="must be a YAML mapping"):
        ov.merge_frontmatter({"name": "x"}, fm, "claude")


def test_merge_frontmatter_empty_overlay_file(ov, tmp_path: Path) -> None:
    fm = _write(tmp_path / "frontmatter.yaml", "")
    merged = ov.merge_frontmatter({"name": "x", "description": "y"}, fm, "claude")
    assert merged == {"name": "x", "description": "y"}


def test_filter_allowed_keys_for_pi(ov) -> None:
    meta = {
        "name": "n",
        "description": "d",
        "argument-hint": "[x]",
        "metadata": {"k": "v"},
        "tools": "a,b",
        "fallbackModels": "m1, m2",
        "systemPromptMode": "replace",
        "defaultReads": "context.md",
        "completionGuard": False,
    }
    out = ov.filter_allowed_keys(meta, "pi")
    assert out == {
        "name": "n",
        "description": "d",
        "metadata": {"k": "v"},
        "tools": "a,b",
        "fallbackModels": "m1, m2",
        "systemPromptMode": "replace",
        "defaultReads": "context.md",
        "completionGuard": False,
    }


def test_filter_allowed_keys_unknown_target(ov) -> None:
    with pytest.raises(ValueError, match="unknown target"):
        ov.filter_allowed_keys({"name": "x"}, "nope")
