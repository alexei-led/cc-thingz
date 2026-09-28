#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = ["python-frontmatter>=1.1"]
# ///
"""Lint agent/skill instructions for cheap structural defects.

Advisory linter — always exits 0. Prints warnings for issues
that the model-based reviewing-instructions skill should verify.

Rubric: src/skills/reviewing-instructions/references/scoring-rubric.md
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import frontmatter

ROOT = next(
    (p for p in [Path.cwd(), *Path.cwd().parents] if (p / "pyproject.toml").is_file()),
    Path.cwd(),
)

CANONICAL_ENTRYPOINTS = {
    "AGENT.md": "agent",
    "AGENTS.md": "instruction",
    "CLAUDE.md": "instruction",
    "SKILL.md": "skill",
}
IGNORE_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    "site-packages",
    "tests",
    "venv",
}
NEGATIVE_NAMES = {"README.md", "CHANGELOG.md", "CONTRIBUTING.md", "LICENSE.md"}
PATH_SIGNAL_DIRS = {
    "agents",
    "skills",
    "prompts",
    "instructions",
    "references",
    "rules",
}
PLATFORM_DIRS = {
    "claude",
    "codex",
    "pi",
    "copilot",
    "cursor",
    "openai",
    "openclaw",
    "hermes",
}
LIKELY_FILE_RE = re.compile(
    r"(?i)^(body|prompt(?:s)?|instruction(?:s)?|rules?|context|policy|system)\.md$"
)
DIRECTIVE_RE = re.compile(
    r"(?i)\b(?:must|should|always|never|do\s+not|use\s+when|read\s+\S+)\b"
)
AGENT_VOCAB_RE = re.compile(
    r"(?i)\b(?:agent|assistant|model|llm|prompt|context|tool|subagent|output|workflow|failure)\b"
)
SECTION_SIGNAL_RE = re.compile(
    r"(?im)^##\s+(?:output|workflow|failure|boundaries|scope|instructions?)\b"
)
MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)#?]+\.md)\)")
INLINE_MD_PATH_RE = re.compile(r"(?<!\w)(?:@)?([A-Za-z0-9_./-]+\.md)(?!\w)")
READ_MD_RE = re.compile(
    r"(?i)\b(?:read|see|follow|use|load|open)\s+`?([A-Za-z0-9_./-]+\.md)`?"
)
_P = re.compile
SKILL_LINE_BUDGET = 500


# -------------------------------------------------------------------
# Types
# -------------------------------------------------------------------


@dataclass
class Finding:
    file: str
    rule_id: str
    message: str


@dataclass
class InstructionFile:
    path: Path
    rel: str
    kind: str  # agent, skill, instruction
    body: str = ""
    description: str = ""
    metadata: dict = field(default_factory=dict)
    entrypoint: bool = True
    origin: str = ""


# -------------------------------------------------------------------
# Discovery
# -------------------------------------------------------------------


def _path_key(path: Path) -> str:
    return str(path.resolve()).lower()


def discover_files() -> list[InstructionFile]:
    files: dict[str, InstructionFile] = {}

    def add(item: InstructionFile | None) -> None:
        if not item:
            return
        files.setdefault(_path_key(item.path), item)

    primary_files: list[InstructionFile] = []

    agents_dir = ROOT / "src" / "agents"
    if agents_dir.is_dir():
        for agent_dir in sorted(agents_dir.iterdir()):
            if not agent_dir.is_dir() or agent_dir.name.startswith("."):
                continue
            md = agent_dir / "AGENT.md"
            if md.exists():
                item = _load(md, kind="agent", entrypoint=True, origin="src/agents")
                add(item)
                if item:
                    primary_files.append(item)

    skills_dir = ROOT / "src" / "skills"
    if skills_dir.is_dir():
        for skill_dir in sorted(skills_dir.iterdir()):
            if not skill_dir.is_dir() or skill_dir.name.startswith("."):
                continue
            sm = skill_dir / "SKILL.md"
            if sm.exists():
                item = _load(sm, kind="skill", entrypoint=True, origin="src/skills")
                add(item)
                if item:
                    primary_files.append(item)

    for item in primary_files:
        for extra in _discover_module_markdown(item):
            add(extra)

    for name, kind in (("AGENTS.md", "instruction"), ("CLAUDE.md", "instruction")):
        for path in sorted(ROOT.rglob(name)):
            if _ignored(path):
                continue
            item = _load(path, kind=kind, entrypoint=True, origin=f"canonical {name}")
            add(item)
            if item:
                for extra in _discover_explicit_references(item):
                    add(extra)

    for path in sorted(ROOT.rglob("*.md")):
        if _path_key(path) in files or _ignored(path):
            continue
        if "docs" in {part.lower() for part in path.parts}:
            continue
        if not _is_likely_instruction_markdown(path):
            continue
        add(
            _load(
                path, kind="instruction", entrypoint=True, origin="heuristic markdown"
            )
        )

    return sorted(files.values(), key=lambda item: item.rel)


def _discover_module_markdown(primary: InstructionFile) -> list[InstructionFile]:
    found: list[InstructionFile] = []
    for path in sorted(primary.path.parent.rglob("*.md")):
        if path == primary.path or _ignored(path):
            continue
        item = _load(
            path,
            kind="instruction",
            entrypoint=False,
            origin=f"support of {primary.rel}",
        )
        if item:
            found.append(item)
    return found


def _discover_explicit_references(item: InstructionFile) -> list[InstructionFile]:
    found: list[InstructionFile] = []
    for path in _extract_markdown_refs(item.path.parent, item.body):
        if _ignored(path) or not path.exists() or path.suffix.lower() != ".md":
            continue
        extra = _load(
            path,
            kind="instruction",
            entrypoint=False,
            origin=f"referenced by {item.rel}",
        )
        if extra:
            found.append(extra)
    return found


def _load(
    path: Path,
    *,
    kind: str,
    entrypoint: bool,
    origin: str,
) -> InstructionFile | None:
    try:
        post = frontmatter.load(str(path))
    except Exception:
        try:
            body = path.read_text()
        except Exception:
            return None
        meta: dict = {}
    else:
        body = post.content
        meta = post.metadata or {}

    rel = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)

    return InstructionFile(
        path=path,
        rel=rel,
        kind=kind,
        body=body,
        description=str(meta.get("description", "")),
        metadata=meta,
        entrypoint=entrypoint,
        origin=origin,
    )


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------


def _ignored(path: Path) -> bool:
    parts = set(path.parts)
    if parts & IGNORE_DIRS:
        return True
    return any(
        part.startswith(".") and part not in {".spec"} for part in path.parts[1:]
    )


def _extract_markdown_refs(base_dir: Path, body: str) -> set[Path]:
    refs: set[Path] = set()
    raw_refs = set(MARKDOWN_LINK_RE.findall(body))
    raw_refs.update(INLINE_MD_PATH_RE.findall(body))
    raw_refs.update(READ_MD_RE.findall(body))
    for raw in raw_refs:
        candidate = raw.strip().strip("`")
        if not candidate or candidate.startswith(("http://", "https://")):
            continue
        path = Path(candidate)
        candidates = []
        if path.is_absolute():
            candidates.append(path)
        else:
            if len(path.parts) == 1 and path.name in CANONICAL_ENTRYPOINTS:
                candidates.append((ROOT / path).resolve())
                candidates.append((base_dir / path).resolve())
            else:
                candidates.append((base_dir / path).resolve())
                candidates.append((ROOT / path).resolve())
        for resolved in candidates:
            if resolved.exists():
                refs.add(resolved)
    return refs


def _is_likely_instruction_markdown(path: Path) -> bool:
    if path.name in NEGATIVE_NAMES:
        return False

    try:
        raw = path.read_text()
    except Exception:
        return False

    score = 0
    lower_parts = {part.lower() for part in path.parts}

    if path.name in CANONICAL_ENTRYPOINTS:
        score += 5
    if LIKELY_FILE_RE.match(path.name):
        score += 4
    if lower_parts & PATH_SIGNAL_DIRS:
        score += 2
    if path.parent.name.lower() in PLATFORM_DIRS and path.name == "body.md":
        score += 4
    if any(
        key in raw for key in ("allowed-tools:", "tools:", "model:", "user-invocable:")
    ):
        score += 3
    if any(key in raw for key in ("name:", "description:")):
        score += 1
    if SECTION_SIGNAL_RE.search(raw):
        score += 2
    if DIRECTIVE_RE.search(raw) and AGENT_VOCAB_RE.search(raw):
        score += 3
    elif DIRECTIVE_RE.search(raw):
        score += 1

    if path.name.startswith("README"):
        score -= 4

    return score >= 6


def _any(body: str, patterns: list[re.Pattern[str]]) -> bool:
    return any(p.search(body) for p in patterns)


# -------------------------------------------------------------------
# Skill structure rules
# -------------------------------------------------------------------


def check_skill_name_clear(f: InstructionFile) -> Finding | None:
    """Skill names should be kebab-case and explainable."""
    if f.kind != "skill" or not f.entrypoint:
        return None
    name = str(f.metadata.get("name", f.path.parent.name))
    if not re.match(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$", name):
        return Finding(f.rel, "K-NAME", f"Skill name '{name}' is not kebab-case.")
    parts = name.split("-")
    if len(name) < 4 or any(len(part) == 1 for part in parts):
        return Finding(
            f.rel,
            "K-NAME",
            f"Skill name '{name}' is too cryptic for broad reuse.",
        )
    return None


def check_skill_description_triggers(f: InstructionFile) -> Finding | None:
    """Skill descriptions drive activation; they need trigger language."""
    if f.kind != "skill" or not f.entrypoint:
        return None
    pats = [
        _P(r"(?i)use\s+when"),
        _P(r"(?i)use\s+for"),
        _P(r"(?i)auto-?activates?"),
        _P(r"(?i)triggers?"),
        _P(r"(?i)when\s+(?:working|user|writing|running|creating)"),
    ]
    if _any(f.description, pats):
        return None
    return Finding(f.rel, "K-DESC", "Skill description lacks clear trigger language.")


def check_progressive_disclosure(f: InstructionFile) -> Finding | None:
    """SKILL.md stays under the line budget; detail moves to references."""
    if f.kind != "skill" or not f.entrypoint:
        return None
    line_count = len(f.body.splitlines())
    if line_count <= SKILL_LINE_BUDGET:
        return None
    return Finding(
        f.rel,
        "K-PROGRESSIVE",
        (
            f"Skill body is {line_count} lines (budget {SKILL_LINE_BUDGET}); "
            "move conditional detail to references/."
        ),
    )


_FENCE_MARKERS = ("```", "~~~")
_INLINE_CODE_RE = re.compile(r"``.+?``|`[^`]+`|\"[^\"]+\"")


def _iter_unfenced_lines(body: str):
    """Yield body lines outside fenced code blocks (``` or ~~~, 3+ chars).

    Fence-delimiter lines themselves are not yielded.
    """
    in_fence = False
    for line in body.splitlines():
        if line.startswith(_FENCE_MARKERS):
            in_fence = not in_fence
            continue
        if not in_fence:
            yield line


def _mask_inline_code(line: str) -> str:
    """Blank code spans and double-quoted mentions so cited tokens are not rules."""
    return _INLINE_CODE_RE.sub(" ", line)


def check_f_no_diagram(f: InstructionFile) -> Finding | None:
    """Mermaid/ASCII diagrams are visual-only; no LLM signal."""
    mermaid_pat = _P(r"```mermaid", re.MULTILINE)
    ascii_pat = _P(r"[+][─\-]+[+]|╔|╗|╚|╝|║", re.MULTILINE)
    if mermaid_pat.search(f.body) or ascii_pat.search(f.body):
        return Finding(
            f.rel,
            "F-NO-DIAGRAM",
            "Contains mermaid or ASCII diagram — remove, no LLM signal.",
        )
    return None


EMPHASIS_RE = re.compile(
    r"\b(?:MANDATORY|CRITICAL|IMPORTANT|MUST|NEVER|ALWAYS)\b"
    r"|(?i:\bthink\s+(?:step[\s-]+by[\s-]+step|carefully|hard)\b)"
)


def check_f_no_emphasis(f: InstructionFile) -> Finding | None:
    """ALL-CAPS emphasis and think-harder exhortations overdrive current models."""
    for line in _iter_unfenced_lines(f.body):
        if match := EMPHASIS_RE.search(_mask_inline_code(line)):
            return Finding(
                f.rel,
                "F-NO-EMPHASIS",
                (
                    f"Contains '{match.group(0)}' — state the rule plainly, "
                    "without caps emphasis or think-harder prompts."
                ),
            )
    return None


# -------------------------------------------------------------------
# Registry
# -------------------------------------------------------------------

ALL_CHECKS = [
    check_skill_name_clear,
    check_skill_description_triggers,
    check_progressive_disclosure,
    check_f_no_diagram,
    check_f_no_emphasis,
]


# -------------------------------------------------------------------
# Scope filtering
# -------------------------------------------------------------------


def _scope_tokens(argv: list[str]) -> list[str]:
    tokens: list[str] = []
    skip_next = False
    for arg in argv:
        if skip_next:
            skip_next = False
            continue
        if arg == "--model":
            skip_next = True
            continue
        if arg.startswith("--"):
            continue
        tokens.append(arg)
    return tokens


def _candidate_scope_paths(token: str) -> list[Path]:
    raw = Path(token)
    paths: list[Path] = []
    if raw.is_absolute():
        paths.append(raw)
    else:
        paths.append((Path.cwd() / raw).resolve())
        paths.append((ROOT / raw).resolve())
        if "/" not in token and "\\" not in token:
            paths.extend(
                [
                    (ROOT / "src" / "skills" / token).resolve(),
                    (ROOT / "src" / "agents" / token).resolve(),
                    (ROOT / "src" / "plugins" / token).resolve(),
                ]
            )
    deduped: list[Path] = []
    seen: set[Path] = set()
    for path in paths:
        if path not in seen:
            deduped.append(path)
            seen.add(path)
    return deduped


def _matches_scope(item: InstructionFile, scope: Path) -> bool:
    item_path = item.path.resolve()
    if scope.is_file():
        return item_path == scope.resolve()
    if scope.is_dir():
        try:
            item_path.relative_to(scope.resolve())
            return True
        except ValueError:
            return False
    return False


def filter_by_scope(
    files: list[InstructionFile], argv: list[str]
) -> list[InstructionFile]:
    tokens = _scope_tokens(argv)
    if not tokens:
        return files

    scopes: list[Path] = []
    for token in tokens:
        for path in _candidate_scope_paths(token):
            if path.exists():
                scopes.append(path.resolve())

    if not scopes:
        return []

    filtered = [
        item for item in files if any(_matches_scope(item, scope) for scope in scopes)
    ]
    return sorted(filtered, key=lambda item: item.rel)


# -------------------------------------------------------------------
# Main
# -------------------------------------------------------------------


def main() -> int:
    files = filter_by_scope(discover_files(), sys.argv[1:])
    if not files:
        print("No instruction files found for scope.")
        return 0

    findings: list[Finding] = []
    for f in files:
        for check in ALL_CHECKS:
            if result := check(f):
                findings.append(result)

    findings.sort(key=lambda x: (x.file, x.rule_id))

    print(f"Instruction lint: {len(files)} files")
    print()

    if not findings:
        print("All checks passed!")
        return 0

    for item in findings:
        print(f"  WARN  [{item.rule_id}] {item.file}")
        print(f"        {item.message}")
    print()
    print(f"Total: {len(findings)} warning(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
