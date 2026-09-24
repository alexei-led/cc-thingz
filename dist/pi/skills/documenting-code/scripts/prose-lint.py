#!/usr/bin/env python3
"""Advisory plain-language lint for Markdown prose.

Usage: prose-lint.py [--max-words N] [--strict] [FILE_OR_DIR ...]

Flags weak modals, contractions, semicolons, filler words, Latin abbreviations,
and sentences longer than --max-words (default 25). Skips front matter, fenced
code, inline code, tables, headings, and HTML. Exit status is 0 unless
--strict is given and there are findings.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SKIP_DIRS = {".git", "node_modules", "dist", "build", "vendor", ".venv", "venv"}
FENCE_RE = re.compile(r"^\s*(```|~~~)")
LIST_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")
RULES = [
    ("modal", re.compile(r"\b(should|would|might|could|may)\b", re.I)),
    (
        "contraction",
        re.compile(
            r"\b\w+(?:n't|'ll|'re|'ve|'d|'m)\b|\b(?:it|that|there|here|what|let)'s\b",
            re.I,
        ),
    ),
    ("semicolon", re.compile(r";")),
    (
        "filler",
        re.compile(
            r"\b(leverage|utilize|seamless(?:ly)?|robust|powerful|simply|just|easily|"
            r"in order to|it is worth noting|out of the box|under the hood)\b",
            re.I,
        ),
    ),
    ("latin", re.compile(r"\b(?:e\.g\.|i\.e\.|etc\.)", re.I)),
]


def markdown_files(args: list[str]) -> list[Path]:
    roots = [Path(a) for a in args] or [Path(".")]
    files: list[Path] = []
    for root in roots:
        if root.is_file():
            files.append(root)
        elif root.is_dir():
            files += [
                p
                for p in sorted(root.rglob("*.md"))
                if not SKIP_DIRS.intersection(p.parts)
            ]
    return files


def prose_units(text: str):
    """Yield (line, text) for each paragraph or list item outside code and tables."""
    lines = text.splitlines()
    start = 0
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                start = i + 1
                break
    in_fence = False
    unit: list[str] = []
    unit_line = 0
    for number, line in enumerate(lines[start:], start=start + 1):
        if FENCE_RE.match(line):
            in_fence = not in_fence
            if unit:
                yield unit_line, " ".join(unit)
                unit = []
            continue
        stripped = line.strip()
        boundary = (
            in_fence
            or not stripped
            or stripped.startswith(("#", "|", "<", ">", "!["))
            or LIST_RE.match(line)
        )
        if boundary and unit:
            yield unit_line, " ".join(unit)
            unit = []
        if in_fence or not stripped or stripped.startswith(("#", "|", "<", "![")):
            continue
        if not unit:
            unit_line = number
        unit.append(LIST_RE.sub("", stripped).lstrip("> "))
    if unit:
        yield unit_line, " ".join(unit)


def clean(text: str) -> str:
    text = re.sub(r"`[^`]*`", "X", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\([^)]*\)", "X", text)
    return re.sub(r"\*\*|__", "", text)


def lint(path: Path, max_words: int) -> list[str]:
    findings = []
    for number, unit in prose_units(path.read_text(encoding="utf-8", errors="replace")):
        text = clean(unit)
        for name, pattern in RULES:
            match = pattern.search(text)
            if match:
                findings.append(
                    f"{path}:{number}: {name}: {match.group(0)!r} in: {unit[:90]}"
                )
        for sentence in re.split(r"(?<=[.!?])\s+", text):
            words = len(sentence.split())
            if words > max_words:
                findings.append(
                    f"{path}:{number}: long-sentence: {words} words: {sentence[:90]}"
                )
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Advisory plain-language lint for Markdown prose."
    )
    parser.add_argument("paths", nargs="*")
    parser.add_argument("--max-words", type=int, default=25)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    findings = [f for p in markdown_files(args.paths) for f in lint(p, args.max_words)]
    for finding in findings:
        print(finding)
    print(f"{len(findings)} findings")
    return 1 if args.strict and findings else 0


if __name__ == "__main__":
    sys.exit(main())
