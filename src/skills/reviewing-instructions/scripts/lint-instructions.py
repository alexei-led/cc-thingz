#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = ["python-frontmatter>=1.1"]
# ///
"""Lint agent/skill instructions against system card rules.

Advisory linter — always exits 0. Prints warnings for issues
that the model-based /reviewing-instructions skill should verify.

Rules: src/skills/reviewing-instructions/references/scoring-rubric.md
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
PLATFORM_DIRS = {"claude", "codex", "gemini", "pi", "openai", "openclaw", "hermes"}
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


# -------------------------------------------------------------------
# Types
# -------------------------------------------------------------------


@dataclass
class Finding:
    file: str
    rule_id: str
    severity: str  # warning, info
    message: str


@dataclass
class InstructionFile:
    path: Path
    rel: str
    model: str
    kind: str  # agent, skill, instruction
    tools: list[str] = field(default_factory=list)
    effort: str | None = None
    user_invocable: bool = False
    body: str = ""
    description: str = ""
    support_files: int = 0
    metadata: dict = field(default_factory=dict)
    entrypoint: bool = True
    origin: str = ""

    @property
    def has_bash(self) -> bool:
        return any("Bash" in t for t in self.tools)

    @property
    def has_risky_bash(self) -> bool:
        risky = (
            "Bash",
            "Bash(*)",
            "Bash(git *)",
            "Bash(make *)",
            "Bash(kubectl *)",
            "Bash(terraform *)",
            "Bash(helm *)",
            "Bash(gcloud *)",
            "Bash(aws *)",
            "Bash(rm *)",
        )
        return any(t in risky for t in self.tools)

    @property
    def has_write_tools(self) -> bool:
        return any(t in self.tools for t in ("Edit", "Write", "MultiEdit"))

    @property
    def has_ask_user_question(self) -> bool:
        return any(t == "AskUserQuestion" for t in self.tools)

    @property
    def is_knowledge_skill(self) -> bool:
        """Auto-activated reference skills (not user-invocable)."""
        return self.kind == "skill" and self.entrypoint and not self.user_invocable


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
            parent=primary,
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
            parent=item,
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
    parent: InstructionFile | None = None,
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

    parent_model = parent.model if parent else None
    model = meta.get(
        "model", parent_model or ("sonnet" if kind in {"agent", "skill"} else "generic")
    )
    model = model.lower() if isinstance(model, str) else (parent_model or "generic")

    tools_raw = (
        meta.get("tools")
        or meta.get("allowed-tools")
        or (parent.tools if parent else [])
    )
    tools = [str(t) for t in tools_raw] if isinstance(tools_raw, list) else []

    effort_val = meta.get("effort") or (parent.effort if parent else None)
    user_invocable = bool(
        meta.get("user-invocable", parent.user_invocable if parent else False)
    )

    support_files = 0
    if kind == "skill" and entrypoint:
        support_files = len(
            [
                p
                for p in path.parent.iterdir()
                if p.name not in {"SKILL.md", "SKILL.codex.md"}
                and not p.name.startswith(".")
            ]
        )

    rel = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)

    return InstructionFile(
        path=path,
        rel=rel,
        model=model,
        kind=kind,
        tools=tools,
        effort=str(effort_val) if effort_val else None,
        user_invocable=user_invocable,
        body=body,
        description=str(meta.get("description", "")),
        support_files=support_files,
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
# Universal rules
# -------------------------------------------------------------------


def check_u_scope(f: InstructionFile) -> Finding | None:
    """Scope boundaries — skip support files and knowledge-base skills."""
    if not f.entrypoint or f.is_knowledge_skill:
        return None
    pats = [
        _P(r"\bONLY\b"),
        _P(r"\bexclusively\b"),
        _P(r"\bDo\s+not\b"),
        _P(r"\bdo\s+NOT\b"),
        _P(r"\bFocus\b.*\bon\b"),
        _P(r"(?i)\bscope\b"),
        _P(r"(?i)out\s*of\s*scope"),
        _P(r"(?i)\$ARGUMENTS"),
        _P(r"(?i)when\s+to\s+skip"),
        _P(r"(?i)avoid\b"),
    ]
    if _any(f.body, pats):
        return None
    return Finding(f.rel, "U-SCOPE", "warning", "No scope boundaries found.")


def check_u_output(f: InstructionFile) -> Finding | None:
    """Output format — skip support files and knowledge-base skills."""
    if not f.entrypoint or f.is_knowledge_skill:
        return None
    pats = [
        _P(r"(?i)output\s*format"),
        _P(r"(?i)##\s*output"),
        _P(r"(?i)##\s*findings"),
        _P(r"(?i)proposal\s*format"),
        _P(r"(?i)example\s*output"),
        _P(r"(?i)##\s*proposed\s*changes"),
        _P(r"(?i)template"),
        _P(r"(?i)##\s*report"),
        _P(r"```\w"),
    ]
    if _any(f.body, pats):
        return None
    return Finding(f.rel, "U-OUTPUT", "warning", "No output format defined.")


def check_u_tool_first(f: InstructionFile) -> Finding | None:
    """Tool-first — only for entrypoint agents with Bash."""
    if not f.entrypoint or not f.has_bash or f.kind != "agent":
        return None
    pats = [
        _P(r"(?i)run\s*tooling"),
        _P(r"(?i)execute\s*these"),
        _P(r"(?i)always\s*execute"),
        _P(r"(?i)run\s*these\s*commands"),
        _P(r"(?i)before\s*(?:manual|starting)"),
        _P(r"```(?:bash|sh)\n"),
    ]
    if _any(f.body, pats):
        return None
    return Finding(
        f.rel,
        "U-TOOL-FIRST",
        "warning",
        "Agent has Bash but no tool-first requirement.",
    )


def check_u_failure(f: InstructionFile) -> Finding | None:
    """Failure handling — skip support files and knowledge-base skills."""
    if not f.entrypoint or f.is_knowledge_skill:
        return None
    pats = [
        _P(r"(?i)\bimpossible\b"),
        _P(r"(?i)\bfail\b"),
        _P(r"(?i)\bunavailable\b"),
        _P(r"(?i)if\s+(?:not|no)\s+(?:available|found)"),
        _P(r"(?i)\bskip\b.*\bsilently\b"),
        _P(r"(?i)no\s+issues\s+found"),
        _P(r"(?i)if\s+clean"),
        _P(r"(?i)report\b.*\bback\b"),
        _P(r"(?i)fall\s*back"),
        _P(r"(?i)edge\s*case"),
        _P(r"(?i)nothing\s+to"),
        _P(r"(?i)stop\s+and\s+(?:ask|report)"),
    ]
    if _any(f.body, pats):
        return None
    return Finding(f.rel, "U-FAILURE", "warning", "No failure/impossibility handling.")


def check_u_ground(f: InstructionFile) -> Finding | None:
    """Grounding in tool output — skip support files and knowledge skills."""
    if not f.entrypoint or f.is_knowledge_skill:
        return None
    pats = [
        _P(r"(?i)include\b.*\boutput\b"),
        _P(r"(?i)\bverify\b"),
        _P(r"(?i)tool\s*(?:output|result)"),
        _P(r"(?i)linter\s*output"),
        _P(r"(?i)\bread\b.*\bbefore\b"),
        _P(r"(?i)cross-reference"),
        _P(r"(?i)check\s*assumption"),
        _P(r"(?i)match\s*existing"),
        _P(r"(?i)cite\b"),
        _P(r"(?i)source\s*url"),
    ]
    if _any(f.body, pats):
        return None
    return Finding(f.rel, "U-GROUND", "warning", "No grounding in tool output.")


def check_u_no_destroy(f: InstructionFile) -> Finding | None:
    """Destructive action warning — only for write-capable entrypoints."""
    if not f.entrypoint or not (f.has_risky_bash or f.has_write_tools):
        return None
    if _any(f.body, [_P(r"(?i)propose\s*only")]):
        return None
    pats = [
        _P(r"(?i)\bdestructive\b"),
        _P(r"(?i)\bcareful\b"),
        _P(r"(?i)\bcaution\b"),
        _P(r"(?i)\bdangerous\b"),
        _P(r"(?i)\birreversible\b"),
        _P(r"(?i)do\s*not\s*(?:delete|remove|modify|overwrite)"),
        _P(r"(?i)\bdry.run\b"),
        _P(r"(?i)--dry-run"),
        _P(r"(?i)\bconfirm\b.*\bbefore\b"),
        _P(r"(?i)\bsafety\b"),
        _P(r"(?i)do\s*not\s*(?:execute|run)\b.*\bcode\b"),
    ]
    if _any(f.body, pats):
        return None
    return Finding(
        f.rel,
        "U-NO-DESTROY",
        "warning",
        "Write-capable but no destructive-action caution.",
    )


# -------------------------------------------------------------------
# Opus rules
# -------------------------------------------------------------------


def check_o_efficiency(f: InstructionFile) -> Finding | None:
    if not f.entrypoint or f.model != "opus":
        return None
    pats = [
        _P(r"(?i)\bfocused\b"),
        _P(r"(?i)don't\s*over"),
        _P(r"(?i)do\s*not\s*(?:over|scan|explore\s*beyond)"),
        _P(r"(?i)\bonly\s*(?:these|flagged|files)\b"),
        _P(r"(?i)\bexclusively\b"),
        _P(r"(?i)limit.*exploration"),
        _P(r"(?i)stop\s*(?:after|once)"),
    ]
    if _any(f.body, pats):
        return None
    return Finding(
        f.rel, "O-EFFICIENCY", "warning", "Opus agent without efficiency constraint."
    )


def check_o_scope_only(f: InstructionFile) -> Finding | None:
    if not f.entrypoint or f.model != "opus":
        return None
    pats = [
        _P(r"ONLY\s*these", re.IGNORECASE),
        _P(r"\bexclusively\b", re.IGNORECASE),
        _P(r"Focus.*ONLY", re.IGNORECASE),
        _P(r"\(ONLY\b"),
    ]
    if _any(f.body, pats):
        return None
    return Finding(
        f.rel, "O-SCOPE-ONLY", "warning", "Opus agent missing 'ONLY these' marker."
    )


# -------------------------------------------------------------------
# Sonnet rules
# -------------------------------------------------------------------


def check_s_anti_eager(f: InstructionFile) -> Finding | None:
    if not f.entrypoint or f.model != "sonnet" or f.is_knowledge_skill:
        return None
    pats = [
        _P(r"(?i)do\s*not\s*fabricat"),
        _P(r"(?i)report.*impossible"),
        _P(r"(?i)do\s*not\s*take\s*unapproved"),
        _P(r"(?i)ask\b.*\bbefore\b"),
        _P(r"(?i)do\s*not\b.*\bworkaround"),
        _P(r"(?i)check\s*with\s*(?:the\s*)?user"),
        _P(r"(?i)stop\s*and\s*(?:ask|report)"),
        _P(r"(?i)don't\b.*\binvent\b"),
        _P(r"(?i)never\b.*\b(?:assume|fabricate)"),
        _P(r"(?i)beyond\s*(?:the\s*)?(?:stated|task)"),
        _P(r"(?i)only\s*(?:when|if)\s*(?:user|asked)"),
        _P(r"(?i)explicit.*request"),
        _P(r"(?i)\bdo\s+not\b"),
        _P(r"(?i)ONLY\s+these"),
        _P(r"(?i)propose\s+only"),
    ]
    if _any(f.body, pats):
        return None
    return Finding(
        f.rel, "S-ANTI-EAGER", "warning", "Sonnet without anti-eagerness clause."
    )


# -------------------------------------------------------------------
# Skill structure rules
# -------------------------------------------------------------------


def check_skill_name_clear(f: InstructionFile) -> Finding | None:
    """Skill names should be kebab-case and explainable."""
    if f.kind != "skill" or not f.entrypoint:
        return None
    name = str(f.metadata.get("name", f.path.parent.name))
    if not re.match(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$", name):
        return Finding(
            f.rel, "K-NAME", "warning", f"Skill name '{name}' is not kebab-case."
        )
    parts = name.split("-")
    if len(name) < 4 or any(len(part) == 1 for part in parts):
        return Finding(
            f.rel,
            "K-NAME",
            "warning",
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
    return Finding(
        f.rel, "K-DESC", "warning", "Skill description lacks clear trigger language."
    )


def check_progressive_disclosure(f: InstructionFile) -> Finding | None:
    """Large skills should move detail into sibling reference files."""
    if f.kind != "skill" or not f.entrypoint:
        return None
    line_count = len(f.body.splitlines())
    if line_count <= 220 or f.support_files > 0:
        return None
    return Finding(
        f.rel,
        "K-PROGRESSIVE",
        "warning",
        (
            f"Skill body is {line_count} lines with no support files; "
            "split reference material."
        ),
    )


_FENCE_MARKERS = ("```", "~~~")
_INLINE_CODE_RE = re.compile(r"``.+?``|`[^`]+`")


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
    """Blank inline code spans so backticked `_names_` aren't read as italics."""
    return _INLINE_CODE_RE.sub(" ", line)


def check_f_no_table(f: InstructionFile) -> Finding | None:
    """Tables waste tokens; bullet lists carry same info."""
    table_pat = _P(r"^\|.+\|.+\|")
    for line in _iter_unfenced_lines(f.body):
        if table_pat.match(line):
            return Finding(
                f.rel,
                "F-NO-TABLE",
                "warning",
                (
                    "Contains markdown tables — replace with bullet lists "
                    "(`- **Label**: desc`). Tables are 3-5x token-heavier "
                    "with no comprehension gain for LLMs."
                ),
            )
    return None


def check_f_no_diagram(f: InstructionFile) -> Finding | None:
    """Mermaid/ASCII diagrams are visual-only; no LLM signal."""
    mermaid_pat = _P(r"```mermaid", re.MULTILINE)
    ascii_pat = _P(r"[+][─\-]+[+]|╔|╗|╚|╝|║", re.MULTILINE)
    if mermaid_pat.search(f.body) or ascii_pat.search(f.body):
        return Finding(
            f.rel,
            "F-NO-DIAGRAM",
            "warning",
            "Contains mermaid or ASCII diagram — remove, no LLM signal.",
        )
    return None


def check_f_no_hr(f: InstructionFile) -> Finding | None:
    """Horizontal rules are low-signal; use ## headers instead."""
    for line in _iter_unfenced_lines(f.body):
        if line.strip() == "---":
            return Finding(
                f.rel,
                "F-NO-HR",
                "info",
                "Contains standalone --- horizontal rule — use ## headers instead.",
            )
    return None


def check_f_no_italic(f: InstructionFile) -> Finding | None:
    """Italic is the lowest-signal markdown element; LLMs ignore it."""
    # Closing boundary is non-whitespace (not [\w]) so label-style italics
    # like _Note:_ or *e.g.:* — which end on punctuation, not a word char —
    # still match.
    italic_pat = _P(r"(?<!\*)\*(?!\*)[\w].*?\S\*(?!\*)|(?<!_)_(?!_)[\w].*?\S_(?!_)")
    for line in _iter_unfenced_lines(f.body):
        if italic_pat.search(_mask_inline_code(line)):
            return Finding(
                f.rel,
                "F-NO-ITALIC",
                "info",
                "Italic (`_text_`) — LLMs ignore it; use bold or plain text.",
            )
    return None


def check_f_bold_sparse(f: InstructionFile) -> Finding | None:
    """Bold overuse trains models to ignore it."""
    prose_lines = 0
    bold_lines = 0
    bold_pat = _P(r"\*\*[^*]+\*\*")
    for line in _iter_unfenced_lines(f.body):
        s = line.strip()
        if not s:
            continue
        prose_lines += 1
        if bold_pat.search(line):
            bold_lines += 1
    if prose_lines == 0:
        return None
    ratio = bold_lines / prose_lines
    if ratio > 0.15:
        return Finding(
            f.rel,
            "F-BOLD-SPARSE",
            "info",
            (
                f"Bold appears on {bold_lines}/{prose_lines} prose lines "
                f"({ratio:.0%}) — keep to ≤15% of lines; reserve "
                "for bullet labels and keywords."
            ),
        )
    return None


def check_one_question_at_a_time(f: InstructionFile) -> Finding | None:
    """Interactive skills should avoid batched interrogation."""
    if not f.entrypoint or not f.has_ask_user_question:
        return None
    pats = [
        _P(r"(?i)one\s+question\s+at\s+a\s+time"),
        _P(r"(?i)ask\s+.*one\s+.*at\s+a\s+time"),
        _P(r"(?i)ask\s+sequential"),
    ]
    if _any(f.body, pats):
        return None
    return Finding(
        f.rel,
        "I-ONE-QUESTION",
        "warning",
        (
            "Uses AskUserQuestion but does not require one-question-at-a-time "
            "or sequential questioning."
        ),
    )


# -------------------------------------------------------------------
# Registry
# -------------------------------------------------------------------

ALL_CHECKS = [
    check_u_scope,
    check_u_output,
    check_u_tool_first,
    check_u_failure,
    check_u_ground,
    check_u_no_destroy,
    check_o_efficiency,
    check_o_scope_only,
    check_s_anti_eager,
    check_skill_name_clear,
    check_skill_description_triggers,
    check_progressive_disclosure,
    check_one_question_at_a_time,
    check_f_no_table,
    check_f_no_diagram,
    check_f_no_hr,
    check_f_no_italic,
    check_f_bold_sparse,
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

    findings.sort(key=lambda x: (x.severity, x.file))

    model_counts: dict[str, int] = {}
    for f in files:
        model_counts[f.model] = model_counts.get(f.model, 0) + 1

    warnings = [x for x in findings if x.severity == "warning"]
    infos = [x for x in findings if x.severity == "info"]

    n_o = model_counts.get("opus", 0)
    n_s = model_counts.get("sonnet", 0)
    n_h = model_counts.get("haiku", 0)
    print(
        f"Instruction lint: {len(files)} files ({n_o} opus, {n_s} sonnet, {n_h} haiku)"
    )
    print()

    if not findings:
        print("All checks passed!")
        return 0

    if warnings:
        print(f"--- WARNINGS ({len(warnings)}) ---")
        for item in warnings:
            print(f"  WARN  [{item.rule_id}] {item.file}")
            print(f"        {item.message}")
        print()

    if infos:
        print(f"--- INFO ({len(infos)}) ---")
        for item in infos:
            print(f"  INFO  [{item.rule_id}] {item.file}")
            print(f"        {item.message}")
        print()

    print(f"Total: {len(warnings)} warning(s), {len(infos)} info(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
