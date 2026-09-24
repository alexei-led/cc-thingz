#!/usr/bin/env python3
"""Render GitHub release notes from the committed CHANGELOG section."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

sys.dont_write_bytecode = True

NOTES_CONTRACT_DIR = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "skills"
    / "releasing-code"
    / "scripts"
)
sys.path.insert(0, str(NOTES_CONTRACT_DIR))

from release_notes import (  # noqa: E402
    ReleaseNotesError,
    budget_for_kind,
    extract_changelog_section,
    render_release_notes,
    validate_notes,
    verify_previous_tag,
    version_from_tag,
)


def build_release_notes(
    changelog_section: str,
    marketplace: dict,
    repository: str,
    tag: str = "v0.0.0",
    previous_tag: str | None = None,
) -> str:
    return render_release_notes(
        tag,
        changelog_section,
        plugin_rows(marketplace),
        repository,
        previous_tag,
    )


def plugin_rows(marketplace: dict) -> list[tuple[str, str]]:
    plugins = marketplace.get("plugins")
    if not isinstance(plugins, list) or not plugins:
        raise ReleaseNotesError(
            "marketplace JSON must contain a non-empty plugins list"
        )

    rows: list[tuple[str, str]] = []
    for plugin in plugins:
        if not isinstance(plugin, dict):
            raise ReleaseNotesError("marketplace plugin entries must be objects")
        name = plugin.get("name")
        description = plugin.get("description")
        if not isinstance(name, str) or not name.strip():
            raise ReleaseNotesError("marketplace plugin is missing name")
        if not isinstance(description, str) or not description.strip():
            raise ReleaseNotesError(f"marketplace plugin {name} is missing description")
        rows.append((name, description))
    return rows


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate GitHub release notes from CHANGELOG.md"
    )
    parser.add_argument("--tag", required=True, help="Release tag, for example v4.9.0")
    parser.add_argument("--changelog", type=Path, default=Path("CHANGELOG.md"))
    parser.add_argument(
        "--marketplace",
        type=Path,
        default=None,
        help="optional legacy marketplace JSON; defaults to package metadata",
    )
    parser.add_argument(
        "--packages-dir", type=Path, default=Path("src/.agentbundler/packages")
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--repository", required=True, help="GitHub repository, for example owner/repo"
    )
    parser.add_argument(
        "--previous-tag",
        help=(
            "append a compare link only when this older tag exists "
            "in the local repository"
        ),
    )
    parser.add_argument(
        "--budget",
        choices=("patch", "minor"),
        default=None,
        help="optional advisory word budget; content is never truncated",
    )
    return parser.parse_args(argv)


def _packages_marketplace(packages_dir: Path) -> dict:
    plugins = []
    for path in sorted(packages_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("id") == "cc-thingz-internal":
            continue
        metadata = data.get("metadata") or {}
        plugins.append(
            {
                "name": data.get("id", path.stem),
                "description": metadata.get("description", ""),
            }
        )
    return {"plugins": plugins}


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        version_from_tag(args.tag)
        changelog_section = extract_changelog_section(
            args.changelog.read_text(encoding="utf-8"), args.tag[1:]
        )
        budget = budget_for_kind(args.budget) if args.budget else None
        report = validate_notes(changelog_section, budget)
        if report.over_budget:
            print(
                f"release notes: advisory budget exceeded for {args.budget} release "
                f"({report.word_count}/{report.budget} words); review for clarity, "
                "but preserve critical migration and known-issue information",
                file=sys.stderr,
            )
        if args.previous_tag:
            verify_previous_tag(args.previous_tag, args.tag, Path.cwd())
        marketplace = (
            json.loads(args.marketplace.read_text(encoding="utf-8"))
            if args.marketplace is not None
            else _packages_marketplace(args.packages_dir)
        )
        notes = build_release_notes(
            changelog_section,
            marketplace,
            args.repository,
            args.tag,
            args.previous_tag,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(notes, encoding="utf-8")
    except (OSError, json.JSONDecodeError, ReleaseNotesError) as exc:
        print(f"release notes: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
