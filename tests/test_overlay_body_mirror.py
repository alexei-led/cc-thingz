"""Tests for `scripts.build.overlay` body mirror mode."""

from __future__ import annotations

import pytest
from conftest import dedent_md


@pytest.fixture(scope="module")
def ov(load_script):
    return load_script("build/overlay.py")


def test_parse_sections_splits_by_header(ov) -> None:
    tree = ov.parse_sections(
        dedent_md(
            """
            # A

            intro

            ## B

            b-body

            ## C

            c-body
            """
        )
    )
    assert tree.level == 0
    assert len(tree.children) == 1
    a = tree.children[0]
    assert a.level == 1
    assert a.title == "A"
    assert "intro" in a.content
    assert [c.title for c in a.children] == ["B", "C"]
    assert "b-body" in a.children[0].content
    assert "c-body" in a.children[1].content


def test_parse_sections_ignores_headers_in_code_fence(ov) -> None:
    tree = ov.parse_sections(
        dedent_md(
            """
            # Real

            ```
            # not a header
            ## also not
            ```

            tail
            """
        )
    )
    assert [c.title for c in tree.children] == ["Real"]
    assert "# not a header" in tree.children[0].content
    assert "tail" in tree.children[0].content


def test_parse_sections_tracks_line_numbers(ov) -> None:
    tree = ov.parse_sections(
        dedent_md(
            """
            # A

            ## B
            """
        )
    )
    a = tree.children[0]
    assert a.line == 1
    assert a.children[0].line == 3


def test_apply_mirror_replaces_section_by_anchor(ov) -> None:
    base = dedent_md(
        """
        # Top

        ## Run linters

        original

        ## Review

        review-body
        """
    )
    overlay = dedent_md(
        """
        # Top

        ## Run linters

        new linter content
        """
    )
    out = ov.apply_mirror(base, overlay)
    assert "original" not in out
    assert "new linter content" in out
    assert "review-body" in out
    # base order preserved
    assert out.find("Run linters") < out.find("Review")


def test_apply_mirror_append_adds_text_at_end(ov) -> None:
    base = dedent_md(
        """
        # Top

        ## Workflow

        base text
        """
    )
    overlay = dedent_md(
        """
        # Top

        ## Workflow (_+)

        appended text
        """
    )
    out = ov.apply_mirror(base, overlay)
    assert "base text" in out
    assert "appended text" in out
    assert out.find("base text") < out.find("appended text")
    # suffix stripped from output header
    assert "(_+)" not in out


def test_apply_mirror_append_with_escaped_suffix(ov) -> None:
    base = dedent_md(
        """
        # Top

        ## Workflow

        base
        """
    )
    overlay = dedent_md(
        """
        # Top

        ## Workflow (\\_+)

        extra
        """
    )
    out = ov.apply_mirror(base, overlay)
    assert out.find("base") < out.find("extra")
    assert "(\\_+)" not in out


def test_apply_mirror_prepend_adds_text_at_start(ov) -> None:
    base = dedent_md(
        """
        # Top

        ## Workflow

        base text
        """
    )
    overlay = dedent_md(
        """
        # Top

        ## Workflow (+_)

        prepended
        """
    )
    out = ov.apply_mirror(base, overlay)
    assert out.find("prepended") < out.find("base text")
    assert "(+_)" not in out


def test_apply_mirror_adds_new_section_under_parent(ov) -> None:
    base = dedent_md(
        """
        # Top

        ## Existing

        e
        """
    )
    overlay = dedent_md(
        """
        # Top

        ## Brand new

        new body
        """
    )
    out = ov.apply_mirror(base, overlay)
    assert "Existing" in out
    assert "Brand new" in out
    assert "new body" in out
    # new section appended after existing
    assert out.find("Existing") < out.find("Brand new")


def test_apply_mirror_missing_append_anchor_raises(ov) -> None:
    base = dedent_md(
        """
        # Top

        ## Other

        x
        """
    )
    overlay = dedent_md(
        """
        # Top

        ## Missing (_+)

        boom
        """
    )
    with pytest.raises(ov.OverlayError, match="append anchor"):
        ov.apply_mirror(base, overlay, overlay_filename="claude/body.md")


def test_apply_mirror_missing_prepend_anchor_raises(ov) -> None:
    base = "# Top\n\n## Other\n\nx\n"
    overlay = "# Top\n\n## Missing (+_)\n\nboom\n"
    with pytest.raises(ov.OverlayError, match="prepend anchor"):
        ov.apply_mirror(base, overlay)


def test_apply_mirror_duplicate_overlay_anchor_raises(ov) -> None:
    base = "# A\n\n## B\n\nx\n"
    overlay = dedent_md(
        """
        # A

        ## B

        first

        ## B

        second
        """
    )
    with pytest.raises(ov.OverlayError, match="duplicate overlay anchor"):
        ov.apply_mirror(base, overlay)


def test_apply_mirror_structural_recurse_does_not_replace_parent(ov) -> None:
    """Overlay header with no direct content + nested children = structural.

    The parent section is not replaced; only the named child is modified.
    """
    base = dedent_md(
        """
        # Top

        ## A

        a-body

        ## B

        b-body
        """
    )
    overlay = dedent_md(
        """
        # Top

        ## A

        new a-body
        """
    )
    out = ov.apply_mirror(base, overlay)
    # A replaced; B preserved
    assert "new a-body" in out
    assert "a-body" in out  # substring still in "new a-body"
    assert "b-body" in out


def test_apply_mirror_full_replace_drops_base_children(ov) -> None:
    """Replace with content under the overlay header drops the base subtree."""
    base = dedent_md(
        """
        # A

        ## A1

        gone

        ## A2

        also gone
        """
    )
    overlay = dedent_md(
        """
        # A

        replacement body
        """
    )
    out = ov.apply_mirror(base, overlay)
    assert "replacement body" in out
    assert "gone" not in out
    assert "A1" not in out
    assert "A2" not in out


def test_apply_mirror_replace_with_content_and_children_merges(ov) -> None:
    """A matched anchor with both content and children merges, not swaps.

    Regression for the H1-collision bug: a Claude overlay pairs an intro
    paragraph under the top header with its own new subsections (the common
    shape). The matched header used to be treated as a leaf and its entire
    base subtree replaced wholesale, silently dropping every base subsection
    the overlay didn't repeat by name.
    """
    base = dedent_md(
        """
        # Top

        base intro

        ## Alpha

        alpha-body

        ## Beta

        beta-body
        """
    )
    overlay = dedent_md(
        """
        # Top

        overlay intro

        ## Beta

        new beta-body

        ## Gamma

        gamma-body
        """
    )
    out = ov.apply_mirror(base, overlay)
    assert "overlay intro" in out
    assert "base intro" not in out
    assert "Alpha" in out
    assert "alpha-body" in out  # untouched base sibling survives
    assert "new beta-body" in out
    assert "Gamma" in out
    assert "gamma-body" in out  # new overlay-only section added


def test_apply_mirror_merge_without_content_keeps_base_intro(ov) -> None:
    """A matched anchor with children but no own content keeps the base intro."""
    base = dedent_md(
        """
        # Top

        base intro

        ## Alpha

        alpha-body
        """
    )
    overlay = dedent_md(
        """
        # Top

        ## Beta

        beta-body
        """
    )
    out = ov.apply_mirror(base, overlay)
    assert "base intro" in out  # no overlay content -> anchor intro survives
    assert "alpha-body" in out
    assert "beta-body" in out


def test_apply_mirror_append_carries_overlay_children(ov) -> None:
    base = dedent_md(
        """
        # Top

        ## Workflow

        base
        """
    )
    overlay = dedent_md(
        """
        # Top

        ## Workflow (_+)

        extra

        ### Detail

        detail-body
        """
    )
    out = ov.apply_mirror(base, overlay)
    assert "base" in out
    assert "extra" in out
    assert "### Detail" in out
    assert "detail-body" in out


def test_apply_mirror_no_overlay_headers_returns_base_unchanged(ov) -> None:
    """Mirror mode with empty overlay tree is a no-op.

    Full-replacement detection is task 4; here, empty overlay tree just means
    no operations to apply.
    """
    base = "# A\n\nhello\n"
    out = ov.apply_mirror(base, "")
    assert out == base


def test_parse_render_round_trip(ov) -> None:
    md = dedent_md(
        """
        # Top

        intro

        ## A

        a-body

        ### A1

        a1-body

        ## B

        b-body
        """
    )
    tree = ov.parse_sections(md)
    # render via internal helper through apply_mirror with empty overlay
    out = ov.apply_mirror(md, "")
    assert out == md
    # spot-check tree shape
    assert tree.children[0].title == "Top"
    assert [c.title for c in tree.children[0].children] == ["A", "B"]
