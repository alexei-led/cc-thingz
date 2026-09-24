#!/usr/bin/env python3
"""Check relative links and #anchors in Markdown files.

Usage: check-links.py [FILE_OR_DIR ...]   (default: current directory)

Checks each relative link target exists and each #anchor matches a heading in
the target file, with GitHub heading slugs. External links (http, https,
mailto) are skipped. Exit status 1 when a link is broken.
"""

from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path

SKIP_DIRS = {".git", "node_modules", "dist", "build", "vendor", ".venv", "venv"}
LINK_RE = re.compile(
    r"(?<!!)\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)|<a\s+[^>]*href=\"([^\"]+)\""
)
IMAGE_RE = re.compile(r"!\[[^\]]*\]\(([^)\s]+)\)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
EXTERNAL = ("http://", "https://", "mailto:", "tel:", "ftp://")


def slugify(text: str) -> str:
    """GitHub-style slug: lowercase, drop punctuation, spaces to hyphens."""
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = text.strip().lower()
    kept = []
    for ch in text:
        category = unicodedata.category(ch)
        if ch in " -_" or category[0] in "LN" or category == "Mn":
            kept.append(ch)
    return "".join(kept).replace(" ", "-")


def unfenced_lines(text: str):
    in_fence = False
    for number, line in enumerate(text.splitlines(), start=1):
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if not in_fence:
            yield number, line


def anchors_of(path: Path, cache: dict[Path, set[str]]) -> set[str]:
    if path not in cache:
        seen: dict[str, int] = {}
        anchors: set[str] = set()
        text = path.read_text(encoding="utf-8", errors="replace")
        for _, line in unfenced_lines(text):
            match = HEADING_RE.match(line)
            if not match:
                continue
            base = slugify(match.group(2))
            count = seen.get(base, 0)
            anchors.add(base if count == 0 else f"{base}-{count}")
            seen[base] = count + 1
        anchors.update(re.findall(r"<a\s+(?:name|id)=\"([^\"]+)\"", text))
        cache[path] = anchors
    return cache[path]


def markdown_files(args: list[str]) -> list[Path]:
    roots = [Path(a) for a in args] or [Path(".")]
    files: list[Path] = []
    for root in roots:
        if root.is_file():
            files.append(root)
        elif root.is_dir():
            for path in sorted(root.rglob("*.md")):
                if not SKIP_DIRS.intersection(path.parts):
                    files.append(path)
        else:
            print(f"{root}: not found", file=sys.stderr)
    return files


def check(files: list[Path]) -> int:
    cache: dict[Path, set[str]] = {}
    broken = 0
    checked = 0
    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        for number, line in unfenced_lines(text):
            line = re.sub(r"`[^`]*`", "", line)
            targets = [m.group(1) or m.group(2) for m in LINK_RE.finditer(line)]
            targets += IMAGE_RE.findall(line)
            for target in targets:
                if target.startswith(EXTERNAL):
                    continue
                checked += 1
                file_part, _, anchor = target.partition("#")
                dest = (
                    (path.parent / file_part).resolve() if file_part else path.resolve()
                )
                if file_part and not dest.exists():
                    print(f"{path}:{number}: missing file: {target}")
                    broken += 1
                    continue
                if anchor and dest.suffix.lower() == ".md":
                    if anchor.lower() not in anchors_of(dest, cache):
                        print(f"{path}:{number}: missing anchor: {target}")
                        broken += 1
    print(f"checked {checked} links in {len(files)} files, {broken} broken")
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(check(markdown_files(sys.argv[1:])))
