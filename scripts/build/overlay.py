"""Shared overlay engine for the skill/agent/hook compiler.

Frontmatter pipeline:

- `load_base` reads `SKILL.md` / `AGENT.md` (YAML+markdown via `python-frontmatter`)
  and `HOOK.sh` / `HOOK.py` (shell-comment YAML block).
- `merge_frontmatter` layers a per-target `<target>/frontmatter.yaml` overlay on
  the base via `mergedeep.merge` with overlay-side wins, strips the `targets`
  renderer metadata, and filters out keys not allowed for the target.

Body pipeline:

- `parse_sections` splits markdown into a tree keyed by `#+` headers, ignoring
  fenced code blocks.
- `apply_mirror` walks an overlay tree onto a base tree. Each overlay header is
  an anchor; the suffix selects the operation (`(_+)` append, `(+_)` prepend,
  no suffix → replace if base has the anchor, otherwise add as a new
  subsection). Append/prepend without a matching base anchor is a build error.
- `apply_body_overlay` auto-detects mode. Full replacement is used when the
  overlay has no header paths matching base and no append/prepend suffixes
  anywhere; otherwise mirror mode is used. Any header-path overlap (even one)
  forces mirror mode — this is the documented "mixed mode" resolution.

Support-file pipeline:

- `apply_support_files` copies the base `scripts/`, `references/`, `assets/`
  subtrees into the output, then layers per-target overrides from
  `<target>/scripts/` etc. on top. Same relative path → replace; new path →
  add. Executable bits are preserved. There is no deletion mechanism in v1
  (per design): a target cannot remove a base support file.
"""

from __future__ import annotations

import logging
import re
import shutil
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import frontmatter
import mergedeep
import yaml

log = logging.getLogger("compile.overlay")


# Keys allowed in the emitted frontmatter per target. Anything outside this set
# is dropped during the merge so a Claude-only field (e.g. `argument-hint`) does
# not leak into Codex/Gemini/Pi output. Sets are inclusive across skills and
# agents — per-kind validation lives in the skill/agent pipelines.
#
# Common base keys (agentskills.io): `name`, `description`, `license`,
# `metadata`. Each target adds the extensions documented in
# `docs/skill-compiler-design.md`.
ALLOWED_KEYS: dict[str, frozenset[str]] = {
    "claude": frozenset(
        {
            "name",
            "description",
            "license",
            "metadata",
            "allowed-tools",
            "when_to_use",
            "argument-hint",
            "arguments",
            "disable-model-invocation",
            "user-invocable",
            "context",
            "hooks",
            "paths",
            "shell",
            "tools",
            "model",
            "color",
            "effort",
            "skills",
            "agent",
        }
    ),
    "codex": frozenset(
        {
            "name",
            "description",
            "model",
            "model_reasoning_effort",
            # Vendor-neutral alias renamed to model_reasoning_effort by codex_toml.
            "effort",
            "sandbox_mode",
            "nickname_candidates",
            "mcp_servers",
            "skills",
        }
    ),
    "gemini": frozenset(
        {
            "name",
            "description",
            "license",
            "metadata",
            "allowed-tools",
            "tools",
            "max_turns",
        }
    ),
    "pi": frozenset(
        {
            "name",
            "description",
            "license",
            "metadata",
            "disable-model-invocation",
            "model",
            "thinking",
            "tools",
            "skills",
            "max_turns",
            "prompt_mode",
            "memory",
            "isolation",
            "disallowed_tools",
        }
    ),
}


# Renderer-only metadata stripped from every emitted frontmatter.
RENDERER_KEYS: frozenset[str] = frozenset({"targets"})


def load_base(path: Path) -> tuple[dict[str, Any], str]:
    """Return `(metadata, body)` for a base source file.

    Markdown files use python-frontmatter. Shell/Python files use a top-of-file
    `# ---` … `# ---` YAML comment block (optionally preceded by a shebang).
    Files with no parseable frontmatter return an empty dict and the full text
    as body.
    """
    text = path.read_text()
    if path.suffix == ".md":
        post = frontmatter.loads(text)
        return dict(post.metadata), post.content
    return _parse_shell_frontmatter(text)


def merge_frontmatter(
    base_meta: Mapping[str, Any],
    overlay_path: Path | None,
    target: str,
) -> dict[str, Any]:
    """Merge per-target frontmatter overlay onto base, filter to allowed keys.

    `mergedeep.merge` defaults to recursive dict merge and replacement for
    scalars/lists — that matches the design's "overlay-side wins, no delete"
    rule. The `targets` renderer key is stripped before key-filtering so it
    never reaches dist/.
    """
    if target not in ALLOWED_KEYS:
        raise ValueError(f"unknown target {target!r}")

    merged: dict[str, Any] = dict(mergedeep.merge({}, dict(base_meta)))

    if overlay_path is not None and overlay_path.exists():
        overlay_raw = yaml.safe_load(overlay_path.read_text())
        if overlay_raw is None:
            overlay_raw = {}
        if not isinstance(overlay_raw, Mapping):
            raise ValueError(
                f"{overlay_path}: frontmatter overlay must be a YAML mapping, "
                f"got {type(overlay_raw).__name__}"
            )
        merged = dict(mergedeep.merge({}, merged, dict(overlay_raw)))

    for key in RENDERER_KEYS:
        merged.pop(key, None)

    return filter_allowed_keys(merged, target)


def target_listed(base_meta: Mapping[str, Any], target: str) -> bool:
    """Return True when `target` passes the base `targets:` restriction."""
    raw = base_meta.get("targets")
    if raw is None:
        return True
    listed = [raw] if isinstance(raw, str) else list(raw)
    return target in listed


def render_md(meta: Mapping[str, Any], body: str) -> str:
    """Render `meta` as YAML frontmatter followed by `body`.

    Uses python-frontmatter for byte-for-byte compatibility with how base
    files are read. Bodies always end with a single trailing newline.
    """
    post = frontmatter.Post(body, **dict(meta))
    text = frontmatter.dumps(post)
    if not text.endswith("\n"):
        text += "\n"
    return text


def filter_allowed_keys(meta: Mapping[str, Any], target: str) -> dict[str, Any]:
    """Drop keys not in the target's allowlist; log each drop at debug level."""
    if target not in ALLOWED_KEYS:
        raise ValueError(f"unknown target {target!r}")
    allowed = ALLOWED_KEYS[target]
    out: dict[str, Any] = {}
    for k, v in meta.items():
        if k in allowed:
            out[k] = v
        else:
            log.debug("target=%s drop key %r (not in allowlist)", target, k)
    return out


def _parse_shell_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Extract `# ---` YAML block at the top of a shell/python source file."""
    lines = text.splitlines(keepends=True)
    i = 0
    if i < len(lines) and lines[i].startswith("#!"):
        i += 1
    while i < len(lines) and lines[i].strip() == "":
        i += 1
    if i >= len(lines) or lines[i].rstrip() != "# ---":
        return {}, text

    fm_start = i
    i += 1
    fm_body_lines: list[str] = []
    while i < len(lines):
        if lines[i].rstrip() == "# ---":
            i += 1
            yaml_src = "\n".join(_strip_comment(ln) for ln in fm_body_lines)
            data = yaml.safe_load(yaml_src) or {}
            if not isinstance(data, Mapping):
                raise ValueError(
                    "shell frontmatter must be a YAML mapping, "
                    f"got {type(data).__name__}"
                )
            body = "".join(lines[:fm_start]) + "".join(lines[i:])
            return dict(data), body
        fm_body_lines.append(lines[i])
        i += 1
    # Opening `# ---` was found but no closing fence — treat as a malformed
    # source rather than silently returning empty metadata.
    raise ValueError("shell frontmatter: opening '# ---' has no matching close")


def _strip_comment(line: str) -> str:
    raw = line.rstrip("\n")
    if raw.startswith("# "):
        return raw[2:]
    if raw.startswith("#"):
        return raw[1:]
    return raw


# --- Body mirror overlay -----------------------------------------------------

_HEADER_RE = re.compile(r"^(#+)\s+(.+?)\s*$")
_FENCE_RE = re.compile(r"^(```+|~~~+)")
_SUFFIX_RE = re.compile(r"\s*\((?:\\?_\+|\+\\?_)\)\s*$")


class OverlayError(ValueError):
    """Raised when an overlay body cannot be merged onto its base."""


@dataclass
class Section:
    """A markdown section: header + its content text + nested subsections.

    The synthetic root has `level=0` and no `raw_header`; everything in the
    parsed document hangs off its `children`.
    """

    level: int
    title: str
    raw_header: str
    content: str
    line: int = 0
    children: list[Section] = field(default_factory=list)


def parse_sections(md: str) -> Section:
    """Parse markdown into a header-keyed tree.

    Lines starting with `#+` outside fenced code blocks become section
    boundaries. Content between a header and the next header at the same or
    higher level is the section's `content`; deeper headers become `children`.
    """
    root = Section(level=0, title="", raw_header="", content="", line=0)
    stack: list[Section] = [root]
    in_fence = False
    fence_chars = ""
    pending: list[str] = []

    def flush() -> None:
        if pending:
            stack[-1].content += "".join(pending)
            pending.clear()

    for idx, line in enumerate(md.splitlines(keepends=True), start=1):
        body = line.rstrip("\n")
        if in_fence:
            pending.append(line)
            if body.strip() == fence_chars:
                in_fence = False
                fence_chars = ""
            continue
        fence_match = _FENCE_RE.match(body)
        if fence_match:
            in_fence = True
            fence_chars = fence_match.group(1)
            pending.append(line)
            continue
        header_match = _HEADER_RE.match(body)
        if header_match:
            flush()
            level = len(header_match.group(1))
            title = header_match.group(2)
            while stack[-1].level >= level:
                stack.pop()
            section = Section(
                level=level,
                title=title,
                raw_header=body,
                content="",
                line=idx,
            )
            stack[-1].children.append(section)
            stack.append(section)
            continue
        pending.append(line)

    flush()
    return root


def _normalize(title: str) -> tuple[str, str]:
    """Return `(key, op)` for an overlay header title.

    `op` is `'append'` for `(_+)`/`(\\_+)`, `'prepend'` for `(+_)`/`(+\\_)`,
    otherwise `'replace'`. The backslash variants exist because markdown
    rendering escapes underscores; either form is accepted.
    """
    stripped = title.rstrip()
    for marker in ("(_+)", "(\\_+)"):
        if stripped.endswith(marker):
            return stripped[: -len(marker)].rstrip(), "append"
    for marker in ("(+_)", "(+\\_)"):
        if stripped.endswith(marker):
            return stripped[: -len(marker)].rstrip(), "prepend"
    return stripped, "replace"


def _strip_suffix(raw_header: str) -> str:
    return _SUFFIX_RE.sub("", raw_header)


def apply_mirror(
    base_body: str,
    overlay_body: str,
    *,
    overlay_filename: str = "<overlay>",
) -> str:
    """Apply an overlay body to a base body in mirror mode.

    Each overlay header is matched to the base by full header path. The suffix
    on the overlay title selects the operation (replace/append/prepend); a
    title with no suffix that does not exist in base is added as a new
    subsection. Duplicate anchors and append/prepend onto a missing base
    anchor raise `OverlayError`.

    A matched `replace` anchor with nested overlay children merges: the
    anchor's own content is replaced if the overlay provides any, and nested
    children are merged recursively by the same rules, so base subsections the
    overlay never mentions survive. A matched anchor with no overlay children
    is a leaf swap — the whole base subtree is replaced.
    """
    base = parse_sections(base_body)
    overlay = parse_sections(overlay_body)
    _merge(base, overlay, [], overlay_filename)
    return _render(base)


def _merge(
    base: Section,
    overlay: Section,
    path: list[str],
    overlay_filename: str,
) -> None:
    seen: set[str] = set()
    for child in overlay.children:
        key, _ = _normalize(child.title)
        if key in seen:
            raise OverlayError(
                f"{overlay_filename}:{child.line}: duplicate overlay anchor "
                f"{'/'.join(path + [key]) or key!r}"
            )
        seen.add(key)

    base_by_key: dict[str, Section] = {}
    for child in base.children:
        key, _ = _normalize(child.title)
        if key in base_by_key:
            raise OverlayError(
                f"<base>:{child.line}: duplicate base anchor "
                f"{'/'.join(path + [key]) or key!r}"
            )
        base_by_key[key] = child

    for overlay_child in overlay.children:
        key, op = _normalize(overlay_child.title)
        target = base_by_key.get(key)
        has_content = overlay_child.content.strip() != ""
        has_children = bool(overlay_child.children)

        if op == "replace":
            if target is None:
                new_section = _clone_for_emit(overlay_child)
                base.children.append(new_section)
                base_by_key[key] = new_section
                continue
            if has_children:
                # Overlay carries its own nested sections: this is a merge, not
                # a full swap. Replace the anchor's own content (the intro text
                # above the first subheader) if the overlay provides any, then
                # recurse so unmentioned base subsections survive. Without this
                # branch, a matched top-level H1 that pairs an intro paragraph
                # with new subsections (the common Claude-overlay shape) wiped
                # every base subsection the overlay didn't repeat — the
                # "H1 collision" bug.
                if has_content:
                    target.content = overlay_child.content
                _merge(target, overlay_child, path + [key], overlay_filename)
            else:
                replacement = _clone_for_emit(overlay_child)
                replacement.raw_header = target.raw_header
                idx = base.children.index(target)
                base.children[idx] = replacement
                base_by_key[key] = replacement
        elif op == "append":
            if target is None:
                raise OverlayError(
                    f"{overlay_filename}:{overlay_child.line}: append anchor "
                    f"{'/'.join(path + [key]) or key!r} not found in base"
                )
            target.content = _join_content(target.content, overlay_child.content)
            target.children.extend(_clone_for_emit(c) for c in overlay_child.children)
        elif op == "prepend":
            if target is None:
                raise OverlayError(
                    f"{overlay_filename}:{overlay_child.line}: prepend anchor "
                    f"{'/'.join(path + [key]) or key!r} not found in base"
                )
            target.content = _join_content(overlay_child.content, target.content)
            new_children = [_clone_for_emit(c) for c in overlay_child.children]
            new_children.extend(target.children)
            target.children = new_children


def _clone_for_emit(section: Section) -> Section:
    return Section(
        level=section.level,
        title=section.title,
        raw_header=_strip_suffix(section.raw_header),
        content=section.content,
        line=section.line,
        children=[_clone_for_emit(c) for c in section.children],
    )


def _join_content(first: str, second: str) -> str:
    a = first.rstrip("\n")
    b = second.lstrip("\n")
    if not a:
        return second
    if not b:
        return first
    return a + "\n\n" + b


def _render(section: Section) -> str:
    parts: list[str] = []
    if section.raw_header:
        parts.append(section.raw_header)
        if not section.raw_header.endswith("\n"):
            parts.append("\n")
    parts.append(section.content)
    for child in section.children:
        _pad_blank_line(parts)
        parts.append(_render(child))
    return "".join(parts)


def _pad_blank_line(parts: list[str]) -> None:
    """Ensure the text accumulated in `parts` ends with a blank line.

    A merge can append a new anchor after a section, or recurse into a
    matched one, whose original source content ended right at EOF or the
    next same-level header with no spare blank line. Without this, the next
    child's header renders glued directly onto the prior paragraph.
    """
    if not parts:
        return
    tail = parts[-1]
    if tail.strip() and not tail.endswith("\n\n"):
        parts[-1] = tail.rstrip("\n") + "\n\n"


# --- Body overlay mode detection ---------------------------------------------


def apply_body_overlay(
    base_body: str,
    overlay_body: str,
    *,
    overlay_filename: str = "<overlay>",
) -> str:
    """Apply overlay to base, auto-detecting mirror vs full-replacement.

    Full-replacement mode emits `overlay_body` as-is (base is dropped). It is
    selected when the overlay has no header paths matching base and no
    `(_+)`/`(+_)` operations anywhere — typical of a target whose body diverges
    by 50%+ from the base (e.g. terser Pi variants).

    Mirror mode is selected when the overlay shares at least one header path
    with the base, OR when it contains any append/prepend suffix. Mixed cases
    (some headers match, some don't) resolve to mirror — non-matching overlay
    headers are added as new sections under their parent, per `apply_mirror`.

    Empty overlay returns base unchanged.
    """
    if not overlay_body.strip():
        return base_body
    base_tree = parse_sections(base_body)
    overlay_tree = parse_sections(overlay_body)
    if _is_full_replacement(base_tree, overlay_tree):
        return overlay_body
    return apply_mirror(base_body, overlay_body, overlay_filename=overlay_filename)


def _is_full_replacement(base: Section, overlay: Section) -> bool:
    if _has_op_suffix(overlay):
        return False
    overlay_paths = set(_header_paths(overlay, ()))
    if not overlay_paths:
        return True
    base_paths = set(_header_paths(base, ()))
    return overlay_paths.isdisjoint(base_paths)


def _has_op_suffix(section: Section) -> bool:
    for child in section.children:
        _, op = _normalize(child.title)
        if op != "replace":
            return True
        if _has_op_suffix(child):
            return True
    return False


def _header_paths(
    section: Section, prefix: tuple[str, ...]
) -> Iterator[tuple[str, ...]]:
    for child in section.children:
        key, _ = _normalize(child.title)
        path = (*prefix, key)
        yield path
        yield from _header_paths(child, path)


# --- Support-file overlay ----------------------------------------------------

SUPPORT_DIRS: tuple[str, ...] = ("scripts", "references", "assets")


def apply_support_files(
    base_dir: Path,
    target: str,
    output_dir: Path,
) -> list[Path]:
    """Copy base support trees, then layer the target's overrides on top.

    Walks `scripts/`, `references/`, `assets/` under `base_dir` and copies each
    file into `output_dir` at the same relative path. Then walks the same
    subtrees under `base_dir/<target>/` and copies on top (same relative path
    replaces an existing file; a new relative path adds one). File mode is
    preserved via `shutil.copystat` so the executable bit survives.

    Missing subtrees are silently skipped (no support files of that kind).
    Returns the list of written destination paths for logging/testing.
    """
    written: list[Path] = []
    for sub in SUPPORT_DIRS:
        base_src = base_dir / sub
        if base_src.is_dir():
            written.extend(_copy_tree(base_src, output_dir / sub))
    for sub in SUPPORT_DIRS:
        overlay_src = base_dir / target / sub
        if overlay_src.is_dir():
            written.extend(_copy_tree(overlay_src, output_dir / sub))
    return written


def _copy_tree(src: Path, dst: Path) -> list[Path]:
    """Copy every regular file under `src` to the matching path under `dst`.

    Uses `shutil.copy2` for content + mtime, then `shutil.copystat` so the
    executable bit propagates. Directories are created lazily. Same-path files
    in `dst` are overwritten — this is how the overlay semantics work.
    """
    written: list[Path] = []
    for entry in src.rglob("*"):
        if not entry.is_file() or entry.is_symlink():
            continue
        rel = entry.relative_to(src)
        out = dst / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(entry, out)
        shutil.copystat(entry, out)
        written.append(out)
    return written
