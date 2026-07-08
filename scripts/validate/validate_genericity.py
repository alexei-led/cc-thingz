#!/usr/bin/env python3
"""Detect Claude-only tokens in vendor-neutral base SKILL.md / AGENT.md files.

Base files under `src/skills/<name>/SKILL.md` and `src/agents/<name>/AGENT.md`
are expected to be runtime-agnostic; target-specific syntax belongs in
`<target>/body.md` overlays.

Forbidden token patterns:

- `$ARGUMENTS`            — Claude slash-command argument substitution
- `Task(`                 — Claude `Task` tool call syntax
- `AskUserQuestion`       — Claude question tool literal name
- `TaskCreate`            — Claude task scheduling tool name
- `TodoWrite`             — Claude todo-list tool name
- `mcp__...`              — Model Context Protocol tool prefix (Claude/Codex)
- `` !`...` ``            — Claude inline-shell preprocessor backticks
- `${CLAUDE_*}`           — Claude-specific env variable substitution

Opt-out: base frontmatter `targets: [claude]` (or `targets: claude`) marks the
artifact as Claude-only on purpose — the validator skips it then.
"""

from __future__ import annotations

import re
import sys
from collections.abc import Iterable
from pathlib import Path

try:
    import frontmatter
except ImportError:
    print("ERROR: pip install python-frontmatter", file=sys.stderr)
    sys.exit(1)

ROOT = next(
    p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").is_file()
)

FORBIDDEN_PATTERN = re.compile(
    r"\$ARGUMENTS"
    r"|\$[1-9][0-9]*\b"
    r"|Task\("
    r"|\bAskUserQuestion\b"
    r"|\bTaskCreate\b"
    r"|\bTodoWrite\b"
    r"|mcp__[A-Za-z0-9_]+"
    r"|!`[^`]+`"
    r"|\$\{CLAUDE_[A-Z_]+\}"
)


def _is_claude_only(meta: dict) -> bool:
    """Return True when base frontmatter restricts the artifact to Claude."""
    raw = meta.get("targets")
    if raw is None:
        return False
    if isinstance(raw, str):
        names = [raw.strip()]
    elif isinstance(raw, Iterable):
        names = [str(t).strip() for t in raw]
    else:
        return False
    names = [n for n in names if n]
    return bool(names) and all(n == "claude" for n in names)


def _body_start_line(raw: str) -> int:
    """Return the 1-based line number where the markdown body begins.

    For a file with `---`/`---` frontmatter, returns the line right after
    the closing fence; for a file without frontmatter, returns 1.
    """
    if not raw.startswith("---"):
        return 1
    lines = raw.splitlines()
    for i in range(1, len(lines)):
        if lines[i].rstrip() == "---":
            return i + 2
    return 1


def scan_file(path: Path) -> list[str]:
    """Return human-readable violation lines for one base file.

    Empty list means clean. Files with `targets: [claude]` short-circuit
    and return no violations regardless of body content.
    """
    raw = path.read_text()
    try:
        post = frontmatter.loads(raw)
    except Exception as exc:
        return [f"ERROR: {path}: invalid frontmatter: {exc}"]

    if _is_claude_only(post.metadata):
        return []

    try:
        rel: Path = path.relative_to(ROOT)
    except ValueError:
        rel = path

    body_start = _body_start_line(raw)
    lines = raw.splitlines()
    violations: list[str] = []
    for idx in range(body_start - 1, len(lines)):
        line = lines[idx]
        line_number = idx + 1
        for match in FORBIDDEN_PATTERN.finditer(line):
            token = match.group(0)
            violations.append(
                f'ERROR: {rel}:{line_number}: token "{token}" not allowed '
                f"in vendor-neutral base; move to claude/body.md or restrict "
                f"to targets: [claude]"
            )
    return violations


def discover_base_files(root: Path = ROOT) -> list[Path]:
    """Return sorted vendor-neutral source files under src/.

    Includes base SKILL.md / AGENT.md plus non-Claude overlay bodies
    (`<target>/body.md` for codex, gemini, pi). The `claude/body.md`
    overlay is intentionally excluded — it is allowed to use Claude
    syntax.
    """
    src = root / "src"
    if not src.is_dir():
        return []
    skills = sorted(src.glob("skills/*/SKILL.md"))
    agents = sorted(src.glob("agents/*/AGENT.md"))
    overlays: list[Path] = []
    for target in ("codex", "gemini", "pi"):
        overlays.extend(sorted(src.glob(f"skills/*/{target}/body.md")))
        overlays.extend(sorted(src.glob(f"agents/*/{target}/body.md")))
    return skills + agents + overlays


def main() -> int:
    violations: list[str] = []
    for path in discover_base_files():
        violations.extend(scan_file(path))

    if violations:
        for v in violations:
            print(v)
        print(f"\n{len(violations)} genericity violation(s)")
        return 1

    print("Genericity check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
