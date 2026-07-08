"""Per-target skill compilation pipeline.

Orchestrates the overlay engine to turn a `src/skills/<name>/` source tree into
the final `SKILL.md` for a single target, plus its support files. The result
is materialized at one or more `dist/` paths resolved through `output_dirs`.

Steps per call:

1. Load base `SKILL.md` (frontmatter + body).
2. Honor `targets:` restriction — when present and the current target is not
   listed, skip the skill.
3. Merge per-target frontmatter overlay (`<target>/frontmatter.yaml`) onto
   the base via `overlay.merge_frontmatter`; the `targets` key is renderer
   metadata and is stripped from the emitted frontmatter.
4. Apply per-target body overlay (`<target>/body.md`) via
   `overlay.apply_body_overlay` — auto-detects mirror vs full replacement.
5. Inject the per-target preamble (`scripts/build/preambles/<name>.md`) where
   applicable. Claude uses no preamble; Codex/Gemini share `platform.md`; Pi
   uses `pi.md`.
6. Copy base support files (`scripts/`, `references/`, `assets/`) into the
   output dir, then layer per-target overrides.
7. Write the assembled `SKILL.md` (frontmatter + body) to every resolved
   output directory.
"""

from __future__ import annotations

import logging
import sys
from collections.abc import Mapping
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import compile as _compile  # noqa: E402
from overlay import (  # noqa: E402
    apply_body_overlay,
    apply_support_files,
    load_base,
    merge_frontmatter,
    render_md,
    target_listed,
)

log = logging.getLogger("compile.skill")


PREAMBLE_NAMES: Mapping[str, str | None] = {
    "claude": None,
    "codex": "platform.md",
    "gemini": "platform.md",
    "pi": "pi.md",
}


def load_preamble(target: str, root: Path) -> str:
    """Return the per-target preamble text, or empty when none applies."""
    name = PREAMBLE_NAMES.get(target)
    if not name:
        return ""
    path = root / "scripts" / "build" / "preambles" / name
    if not path.is_file():
        raise FileNotFoundError(
            f"preamble {name!r} configured for target {target!r} is missing: {path}"
        )
    return path.read_text().strip()


def output_dirs(
    name: str,
    target: str,
    plugin_index: Mapping[str, list[str]] | None,
    root: Path,
) -> list[Path]:
    """Resolve per-target dist directories for a skill.

    Plugin-grouped targets (`claude`, `codex`) emit once per owning plugin
    from `plugin_index`; an unowned skill returns an empty list (skipped)
    so it can't land at an unreachable flat path that the marketplace
    manifest never references. Flat targets (`gemini`, `pi`) always emit
    to the flat directory.
    """
    cfg = _compile.OUTPUT[target]
    dist = root / "dist" / target
    skill_dir = cfg["skill_dir"]
    if cfg["layout"] == "plugin":
        plugins = list((plugin_index or {}).get(name, []))
        return [dist / "plugins" / p / skill_dir / name for p in plugins]
    return [dist / skill_dir / name]


def _inject_preamble(body: str, preamble: str) -> str:
    if not preamble:
        return body
    return preamble + "\n\n" + body


def compile_skill(
    skill_dir: Path,
    target: str,
    plugin_index: Mapping[str, list[str]] | None,
    root: Path,
) -> list[Path]:
    """Compile a single skill for a single target.

    Returns the list of written `SKILL.md` paths (empty when the skill is
    skipped due to a `targets:` restriction).
    """
    base_path = skill_dir / "SKILL.md"
    if not base_path.is_file():
        raise FileNotFoundError(
            f"skill {skill_dir.name!r}: missing base file {base_path}"
        )
    base_meta, base_body = load_base(base_path)

    if not target_listed(base_meta, target):
        log.debug(
            "skill=%s target=%s skipped (not in targets:%s)",
            skill_dir.name,
            target,
            base_meta.get("targets"),
        )
        return []

    overlay_fm = skill_dir / target / "frontmatter.yaml"
    merged_meta = merge_frontmatter(
        base_meta,
        overlay_fm if overlay_fm.is_file() else None,
        target,
    )

    overlay_body_path = skill_dir / target / "body.md"
    if overlay_body_path.is_file():
        body = apply_body_overlay(
            base_body,
            overlay_body_path.read_text(),
            overlay_filename=str(overlay_body_path),
        )
    else:
        body = base_body

    body = _inject_preamble(body, load_preamble(target, root))

    rendered = render_md(merged_meta, body)

    written: list[Path] = []
    for out_dir in output_dirs(skill_dir.name, target, plugin_index, root):
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "SKILL.md").write_text(rendered)
        apply_support_files(skill_dir, target, out_dir)
        written.append(out_dir / "SKILL.md")
    return written
