#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Sequence
from pathlib import Path

TAG_RE = re.compile(r"^v(?P<version>\d+\.\d+\.\d+)$")
VERSION_HEADER_RE = re.compile(
    r"^## \[(?P<version>\d+\.\d+\.\d+)\](?:\s+-\s+.*)?\s*$", re.MULTILINE
)


class ReleaseNotesError(RuntimeError):
    pass


def version_from_tag(tag: str) -> str:
    match = TAG_RE.fullmatch(tag.strip())
    if match is None:
        raise ReleaseNotesError(f"tag must match vX.Y.Z: {tag}")
    return match.group("version")


def extract_changelog_section(changelog: str, version: str) -> str:
    matches = list(VERSION_HEADER_RE.finditer(changelog))
    for index, match in enumerate(matches):
        if match.group("version") != version:
            continue
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(changelog)
        section = changelog[start:end].strip()
        if not _has_body_content(section):
            raise ReleaseNotesError(f"CHANGELOG.md section for {version} is empty")
        return section
    raise ReleaseNotesError(f"CHANGELOG.md is missing section for {version}")


def build_release_notes(
    changelog_section: str, marketplace: dict, repository: str
) -> str:
    lines = [
        "## Changes",
        "",
        changelog_section,
        "",
        "## Plugins",
        "",
        "| Plugin | Description |",
        "| ------ | ----------- |",
    ]
    for name, description in plugin_rows(marketplace):
        lines.append(f"| **{_markdown_cell(name)}** | {_markdown_cell(description)} |")
    lines.extend(
        [
            "",
            "## Distribution",
            "",
            "Artifacts are rendered by Agent Bundler from the repository root:",
            "",
            "```bash",
            "agbun build --root .",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


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


def _has_body_content(section: str) -> bool:
    return any(
        line.strip() and not line.lstrip().startswith("#")
        for line in section.splitlines()
    )


def _markdown_cell(value: str) -> str:
    return " ".join(value.split()).replace("|", "\\|")


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
    return parser.parse_args(argv)


def _packages_marketplace(packages_dir: Path) -> dict:
    plugins = []
    for path in sorted(packages_dir.glob("*.json")):
        data = json.loads(path.read_text())
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
        version = version_from_tag(args.tag)
        changelog_section = extract_changelog_section(
            args.changelog.read_text(), version
        )
        marketplace = (
            json.loads(args.marketplace.read_text())
            if args.marketplace is not None
            else _packages_marketplace(args.packages_dir)
        )
        notes = build_release_notes(changelog_section, marketplace, args.repository)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(notes)
    except (OSError, json.JSONDecodeError, ReleaseNotesError) as exc:
        print(f"release notes: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
