#!/usr/bin/env python3
"""Validate and render curated release-note content without external dependencies."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tomllib
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

TAG_RE = re.compile(r"^v(?P<version>\d+\.\d+\.\d+)$")
VERSION_HEADER_RE = re.compile(
    r"^## \[(?P<version>\d+\.\d+\.\d+)\](?:\s+-\s+.*)?\s*$", re.MULTILINE
)
LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
WORD_RE = re.compile(r"\b[\w]+(?:[-’'][\w]+)*\b", re.UNICODE)
PLACEHOLDER_RE = re.compile(
    r"^(?:"
    r"release(?:\s+(?:version|v?\d+\.\d+\.\d+|version\s*\d+\.\d+\.\d+|x\.y\.z))?"
    r"|version(?:\s+(?:v?\d+\.\d+\.\d+|x\.y\.z))?"
    r"|v?\d+\.\d+\.\d+"
    r"|todo(?:\s*[:—-].*)?"
    r"|tbd"
    r"|coming\s+soon"
    r"|full\s+changelog"
    r"|compare(?:\s+changes)?"
    r"|add\s+(?:release\s+)?notes?(?:\s+here)?"
    r"|to\s+be\s+determined"
    r")$",
    re.IGNORECASE,
)
COMPARE_URL_RE = re.compile(r"(?:/compare/|compare\.)", re.IGNORECASE)


class ReleaseNotesError(ValueError):
    """Raised when release notes are missing, placeholders, or invalid."""


@dataclass(frozen=True, slots=True)
class NotesReport:
    word_count: int
    budget: int | None

    @property
    def over_budget(self) -> bool:
        return self.budget is not None and self.word_count > self.budget


def version_from_tag(tag: str) -> str:
    match = TAG_RE.fullmatch(tag.strip())
    if match is None:
        raise ReleaseNotesError(f"tag must match vX.Y.Z: {tag}")
    return match.group("version")


def _version_tuple(version: str) -> tuple[int, int, int]:
    major, minor, patch = version_from_tag(version).split(".")
    return int(major), int(minor), int(patch)


def verify_previous_tag(
    previous_tag: str, current_tag: str, repository_root: Path
) -> None:
    previous_version = _version_tuple(previous_tag)
    current_version = _version_tuple(current_tag)
    if previous_version >= current_version:
        raise ReleaseNotesError(
            f"previous tag {previous_tag} is not older than {current_tag}"
        )
    result = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", f"refs/tags/{previous_tag}"],
        cwd=repository_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise ReleaseNotesError(f"previous tag {previous_tag} is not present locally")


def collect_release_versions(root: Path) -> dict[str, str]:
    versions: dict[str, str] = {}

    def add(label: str, value: object) -> None:
        if not isinstance(value, str) or not re.fullmatch(r"\d+\.\d+\.\d+", value):
            raise ReleaseNotesError(f"invalid release version in {label}: {value!r}")
        versions[label] = value

    try:
        project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
        project_name = project["project"]["name"]
        add("pyproject.toml", project["project"]["version"])
        lock = tomllib.loads((root / "uv.lock").read_text(encoding="utf-8"))
        locked_projects = [
            package
            for package in lock["package"]
            if package.get("name") == project_name
        ]
        if len(locked_projects) != 1:
            raise ReleaseNotesError(
                f"uv.lock must contain exactly one {project_name} project package"
            )
        add("uv.lock", locked_projects[0]["version"])
        bundle = json.loads((root / "agentbundle.json").read_text(encoding="utf-8"))
        add("agentbundle.json distribution", bundle["distribution"]["version"])
        for index, composition in enumerate(bundle.get("composition", [])):
            aggregate = composition.get("aggregate")
            if aggregate is not None:
                add(
                    f"agentbundle.json composition {index}",
                    aggregate["metadata"]["version"],
                )
        manifests = sorted((root / "src/.agentbundler/packages").glob("*.json"))
        if not manifests:
            raise ReleaseNotesError(
                "no src/.agentbundler/packages/*.json manifests found"
            )
        for path in manifests:
            data = json.loads(path.read_text(encoding="utf-8"))
            add(str(path.relative_to(root)), data["metadata"]["version"])
        for relative in (
            "package.json",
            "src/skills/playwright-skill/scripts/package.json",
        ):
            data = json.loads((root / relative).read_text(encoding="utf-8"))
            add(relative, data["version"])
    except (
        AttributeError,
        KeyError,
        OSError,
        TypeError,
        json.JSONDecodeError,
        tomllib.TOMLDecodeError,
    ) as exc:
        raise ReleaseNotesError(
            f"cannot read release version manifests: {exc}"
        ) from exc
    return versions


def validate_release_version_contract(
    versions: dict[str, str], tag: str | None = None
) -> str:
    if not versions:
        raise ReleaseNotesError("no release version manifests were checked")
    distinct = set(versions.values())
    if len(distinct) != 1:
        details = ", ".join(f"{name}={value}" for name, value in versions.items())
        raise ReleaseNotesError(f"release version manifests disagree: {details}")
    version = next(iter(distinct))
    if tag is not None:
        expected = version_from_tag(tag)
        if version != expected:
            raise ReleaseNotesError(
                f"release tag {tag} does not match "
                f"package/distribution version {version}"
            )
    return version


def extract_changelog_section(changelog: str, version: str) -> str:
    matches = list(VERSION_HEADER_RE.finditer(changelog))
    for index, match in enumerate(matches):
        if match.group("version") != version:
            continue
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(changelog)
        section = changelog[start:end].strip()
        validate_notes(section)
        return section
    raise ReleaseNotesError(f"CHANGELOG.md is missing section for {version}")


def _content_lines(notes: str) -> list[str]:
    content: list[str] = []
    visible_notes = re.sub(r"<!--.*?-->", "", notes, flags=re.DOTALL)
    for line in visible_notes.splitlines():
        stripped = line.strip()
        if (
            not stripped
            or stripped.startswith("#")
            or re.fullmatch(r"[-*_]{3,}", stripped)
        ):
            continue
        stripped = re.sub(r"^\s*(?:[-*+]\s+|\d+[.)]\s+|>\s*)", "", stripped)
        stripped = LINK_RE.sub(
            lambda match: (
                ""
                if COMPARE_URL_RE.search(match.group(2))
                and re.search(r"(?:full\s+)?changelog|compare", match.group(1), re.I)
                else match.group(1)
            ),
            stripped,
        )
        stripped = re.sub(r"https?://\S+", "", stripped)
        stripped = re.sub(r"`([^`]*)`", r"\1", stripped)
        stripped = re.sub(r"[*_~]", "", stripped).strip(" \t-:,.;")
        if not stripped or PLACEHOLDER_RE.fullmatch(stripped):
            continue
        content.append(stripped)
    return content


def validate_notes(notes: str, budget: int | None = None) -> NotesReport:
    if budget is not None and budget < 1:
        raise ValueError("word budget must be positive")
    content = _content_lines(notes)
    if not content:
        raise ReleaseNotesError("release notes need meaningful user-visible content")
    word_count = len(WORD_RE.findall(" ".join(content)))
    return NotesReport(word_count=word_count, budget=budget)


def budget_for_kind(kind: str) -> int:
    if kind == "patch":
        return 150
    if kind == "minor":
        return 250
    raise ValueError(f"unsupported release kind: {kind}")


def validate_repository(repository: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ReleaseNotesError(f"repository must be owner/name: {repository}")
    return repository


def validate_release_identity(
    identity: dict[str, object],
    tag: str,
    expected_assets: Sequence[str],
    expected_title: str | None = None,
) -> None:
    version_from_tag(tag)
    if identity.get("tagName") != tag:
        raise ReleaseNotesError(f"release identity tag does not match {tag}")
    if identity.get("isDraft") is not False:
        raise ReleaseNotesError("refusing repair of a draft or unknown-state release")
    if identity.get("isPrerelease") is not False:
        raise ReleaseNotesError(
            "refusing repair of a prerelease or unknown-state release"
        )
    assets = identity.get("assets")
    if not isinstance(assets, list) or any(
        not isinstance(asset, dict) or not isinstance(asset.get("name"), str)
        for asset in assets
    ):
        raise ReleaseNotesError("release identity has invalid assets")
    actual_assets = [asset["name"] for asset in assets]
    if sorted(actual_assets) != sorted(expected_assets):
        raise ReleaseNotesError("release assets do not match the expected package set")
    if expected_title is not None and identity.get("name") != expected_title:
        raise ReleaseNotesError(f"release title was not updated to {expected_title}")


def render_release_notes(
    tag: str,
    changelog_section: str,
    plugins: Sequence[tuple[str, str]],
    repository: str,
    previous_tag: str | None = None,
) -> str:
    version_from_tag(tag)
    validate_repository(repository)
    validate_notes(changelog_section)

    lines = ["## Changes", "", changelog_section.strip()]
    if plugins:
        lines.extend(
            [
                "",
                "## Plugins",
                "",
                "| Plugin | Description |",
                "| ------ | ----------- |",
            ]
        )
        lines.extend(
            f"| **{_markdown_cell(name)}** | {_markdown_cell(description)} |"
            for name, description in plugins
        )
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
        ]
    )
    if previous_tag is not None:
        previous_version = _version_tuple(previous_tag)
        if previous_version >= _version_tuple(tag):
            raise ReleaseNotesError(
                f"previous tag {previous_tag} is not older than {tag}"
            )
        lines.extend(
            [
                "",
                "## Full Changelog",
                "",
                f"https://github.com/{repository}/compare/{previous_tag}...{tag}",
            ]
        )
    return "\n".join(lines) + "\n"


def _markdown_cell(value: str) -> str:
    return " ".join(value.split()).replace("|", "\\|")


def _report(report: NotesReport, kind: str) -> None:
    print(f"release notes: {report.word_count} words")
    if report.over_budget:
        print(
            f"release notes: advisory budget exceeded for {kind} release "
            f"({report.word_count}/{report.budget} words); review for clarity, "
            "but do not remove critical migration or known-issue information",
            file=sys.stderr,
        )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    check = subparsers.add_parser("check", help="validate a Markdown notes file")
    check.add_argument("file", type=Path)
    check.add_argument("--budget", choices=("patch", "minor"))
    check_changelog = subparsers.add_parser(
        "check-changelog", help="validate a release section in CHANGELOG.md"
    )
    check_changelog.add_argument("--changelog", type=Path, default=Path("CHANGELOG.md"))
    check_changelog.add_argument(
        "--version", required=True, help="release version X.Y.Z"
    )
    check_changelog.add_argument("--budget", choices=("patch", "minor"))
    check_versions = subparsers.add_parser(
        "check-versions", help="check that release version manifests are synchronized"
    )
    check_versions.add_argument("--root", type=Path, default=Path("."))
    check_versions.add_argument("--tag", help="also require manifests to match vX.Y.Z")
    check_release = subparsers.add_parser(
        "check-release",
        help="validate the release tag, manifests, and changelog section",
    )
    check_release.add_argument("--root", type=Path, default=Path("."))
    check_release.add_argument("--tag", required=True, help="release tag vX.Y.Z")
    check_release.add_argument("--changelog", type=Path, default=Path("CHANGELOG.md"))
    check_release.add_argument("--budget", choices=("patch", "minor"))
    check_identity = subparsers.add_parser(
        "check-release-identity",
        help="reject drafts and verify a published release tag and package assets",
    )
    check_identity.add_argument("--identity", type=Path, required=True)
    check_identity.add_argument("--tag", required=True, help="release tag vX.Y.Z")
    check_identity.add_argument(
        "--expected-asset", action="append", required=True, dest="expected_assets"
    )
    check_identity.add_argument("--title", help="also require the exact release title")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        budget_kind = getattr(args, "budget", None)
        budget = budget_for_kind(budget_kind) if budget_kind else None
        if args.command == "check":
            notes = args.file.read_text(encoding="utf-8")
            report = validate_notes(notes, budget)
        elif args.command == "check-changelog":
            section = extract_changelog_section(
                args.changelog.read_text(encoding="utf-8"), args.version
            )
            report = validate_notes(section, budget)
        elif args.command == "check-versions":
            versions = collect_release_versions(args.root)
            version = validate_release_version_contract(versions, args.tag)
            print(f"release version manifests agree at {version}")
            return 0
        elif args.command == "check-release-identity":
            identity = json.loads(args.identity.read_text(encoding="utf-8"))
            if not isinstance(identity, dict):
                raise ReleaseNotesError("release identity JSON must be an object")
            validate_release_identity(
                identity, args.tag, args.expected_assets, args.title
            )
            print(f"release identity verified for {args.tag}")
            return 0
        else:
            versions = collect_release_versions(args.root)
            validate_release_version_contract(versions, args.tag)
            section = extract_changelog_section(
                args.changelog.read_text(encoding="utf-8"), args.tag[1:]
            )
            budget = budget_for_kind(args.budget) if args.budget else None
            report = validate_notes(section, budget)
        _report(report, args.budget or "release")
    except (OSError, ReleaseNotesError) as exc:
        print(f"release notes: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
