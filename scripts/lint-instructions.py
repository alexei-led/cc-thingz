#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = ["python-frontmatter>=1.1"]
# ///
"""Lint agent/skill instructions against system card rules.

Advisory linter — always exits 0. Prints warnings for issues
that the model-based /linting-instructions skill should verify.

Rules: docs/instruction-lint-rules.md
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import frontmatter

ROOT = Path(__file__).resolve().parent.parent


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
    kind: str  # agent or skill
    tools: list[str] = field(default_factory=list)
    effort: str | None = None
    user_invocable: bool = False
    body: str = ""
    description: str = ""
    support_files: int = 0
    metadata: dict = field(default_factory=dict)

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
        return self.kind == "skill" and not self.user_invocable


# -------------------------------------------------------------------
# Discovery
# -------------------------------------------------------------------


def discover_files() -> list[InstructionFile]:
    files: list[InstructionFile] = []
    plugins_dir = ROOT / "plugins"
    if not plugins_dir.is_dir():
        return files

    for plugin_dir in sorted(plugins_dir.iterdir()):
        if not plugin_dir.is_dir() or plugin_dir.name.startswith("."):
            continue

        agents_dir = plugin_dir / "agents"
        if agents_dir.is_dir():
            for md in sorted(agents_dir.rglob("*.md")):
                if md.name == "README.md":
                    continue
                if f := _load(md, "agent"):
                    files.append(f)

        skills_dir = plugin_dir / "skills"
        if skills_dir.is_dir():
            for sd in sorted(skills_dir.iterdir()):
                if not sd.is_dir() or sd.name.startswith("."):
                    continue
                sm = sd / "SKILL.md"
                if sm.exists():
                    if f := _load(sm, "skill"):
                        files.append(f)
    return files


def _load(path: Path, kind: str) -> InstructionFile | None:
    try:
        post = frontmatter.load(str(path))
    except Exception:
        return None
    if not post.metadata:
        return None

    meta = post.metadata
    model = meta.get("model", "sonnet")
    model = model.lower() if isinstance(model, str) else "sonnet"

    tools_raw = meta.get("tools") or meta.get("allowed-tools") or []
    tools = [str(t) for t in tools_raw] if isinstance(tools_raw, list) else []

    effort_val = meta.get("effort")
    support_files = 0
    if kind == "skill":
        support_files = len(
            [
                p
                for p in path.parent.iterdir()
                if p.name not in {"SKILL.md", "SKILL.codex.md"}
                and not p.name.startswith(".")
            ]
        )

    return InstructionFile(
        path=path,
        rel=str(path.relative_to(ROOT)),
        model=model,
        kind=kind,
        tools=tools,
        effort=str(effort_val) if effort_val else None,
        user_invocable=bool(meta.get("user-invocable", False)),
        body=post.content,
        description=str(meta.get("description", "")),
        support_files=support_files,
        metadata=meta,
    )


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------

_P = re.compile  # alias


def _any(body: str, patterns: list[re.Pattern[str]]) -> bool:
    return any(p.search(body) for p in patterns)


# -------------------------------------------------------------------
# Universal rules
# -------------------------------------------------------------------


def check_u_scope(f: InstructionFile) -> Finding | None:
    """Scope boundaries — skip knowledge-base skills."""
    if f.is_knowledge_skill:
        return None
    pats = [
        _P(r"\bONLY\b"),
        _P(r"\bexclusively\b"),
        _P(r"\bDo\s+not\b"),
        _P(r"\bdo\s+NOT\b"),
        _P(r"\bFocus\b.*\bon\b"),
        _P(r"(?i)\bscope\b"),
        _P(r"(?i)out\s*of\s*scope"),
        _P(r"(?i)\$ARGUMENTS"),  # arg-based scoping
        _P(r"(?i)when\s+to\s+skip"),
        _P(r"(?i)avoid\b"),
    ]
    if _any(f.body, pats):
        return None
    return Finding(
        f.rel,
        "U-SCOPE",
        "warning",
        "No scope boundaries found.",
    )


def check_u_output(f: InstructionFile) -> Finding | None:
    """Output format — skip knowledge-base skills."""
    if f.is_knowledge_skill:
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
        _P(r"```\w"),  # code block with lang hint
    ]
    if _any(f.body, pats):
        return None
    return Finding(
        f.rel,
        "U-OUTPUT",
        "warning",
        "No output format defined.",
    )


def check_u_tool_first(f: InstructionFile) -> Finding | None:
    """Tool-first — only for agents with Bash."""
    if not f.has_bash or f.kind != "agent":
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
    """Failure handling — skip knowledge-base skills."""
    if f.is_knowledge_skill:
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
    return Finding(
        f.rel,
        "U-FAILURE",
        "warning",
        "No failure/impossibility handling.",
    )


def check_u_ground(f: InstructionFile) -> Finding | None:
    """Grounding in tool output — skip knowledge skills."""
    if f.is_knowledge_skill:
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
    return Finding(
        f.rel,
        "U-GROUND",
        "warning",
        "No grounding in tool output.",
    )


def check_u_no_destroy(f: InstructionFile) -> Finding | None:
    """Destructive action warning — only for write-capable agents."""
    if not (f.has_risky_bash or f.has_write_tools):
        return None
    # Propose-only agents are safe
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
    if f.model != "opus":
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
        f.rel,
        "O-EFFICIENCY",
        "warning",
        "Opus agent without efficiency constraint.",
    )


def check_o_scope_only(f: InstructionFile) -> Finding | None:
    if f.model != "opus":
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
        f.rel,
        "O-SCOPE-ONLY",
        "warning",
        "Opus agent missing 'ONLY these' marker.",
    )


# -------------------------------------------------------------------
# Sonnet rules
# -------------------------------------------------------------------


def check_s_anti_eager(f: InstructionFile) -> Finding | None:
    if f.model != "sonnet":
        return None
    if f.is_knowledge_skill:
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
        f.rel,
        "S-ANTI-EAGER",
        "warning",
        "Sonnet without anti-eagerness clause.",
    )


# -------------------------------------------------------------------
# Skill structure rules
# -------------------------------------------------------------------


def check_skill_name_clear(f: InstructionFile) -> Finding | None:
    """Skill names should be kebab-case and explainable."""
    if f.kind != "skill":
        return None
    name = str(f.metadata.get("name", f.path.parent.name))
    if not re.match(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$", name):
        return Finding(
            f.rel,
            "K-NAME",
            "warning",
            f"Skill name '{name}' is not kebab-case.",
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
    if f.kind != "skill":
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
        f.rel,
        "K-DESC",
        "warning",
        "Skill description lacks clear trigger language.",
    )


def check_progressive_disclosure(f: InstructionFile) -> Finding | None:
    """Large skills should move detail into sibling reference files."""
    if f.kind != "skill":
        return None
    line_count = len(f.body.splitlines())
    if line_count <= 220 or f.support_files > 0:
        return None
    return Finding(
        f.rel,
        "K-PROGRESSIVE",
        "warning",
        f"Skill body is {line_count} lines with no support files; "
        "split reference material.",
    )


def check_one_question_at_a_time(f: InstructionFile) -> Finding | None:
    """Interactive skills should avoid batched interrogation."""
    if not f.has_ask_user_question:
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
        "Uses AskUserQuestion but does not require one-question-at-a-time "
        "or sequential questioning.",
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
]


# -------------------------------------------------------------------
# Main
# -------------------------------------------------------------------


def main() -> int:
    files = discover_files()
    if not files:
        print("No instruction files found.")
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
    # Advisory only — never fail CI
    return 0


if __name__ == "__main__":
    sys.exit(main())
