"""Plugin composition index and output-path resolver.

Reads every `src/plugins/<plugin>/plugin.yaml` into a per-kind reverse map
(`name → [owning plugins]`) used by the compiler to determine where each
skill / agent / hook lands in `dist/` for plugin-grouped targets
(`claude`, `codex`).

For flat targets (`gemini`, `pi`) the index is unused — artifacts always
land at the flat per-target path.

Plugin-grouped targets where the artifact is not owned by any plugin emit
no output for that target (the artifact is effectively skipped). Flat
targets always emit so vendor-neutral skills/agents remain available on
Pi even when they have no plugin assignment.
"""

from __future__ import annotations

import logging
import re
import sys
from collections.abc import Mapping
from pathlib import Path

import frontmatter
import yaml

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import compile as _compile  # noqa: E402

log = logging.getLogger("compile.plugin_index")


KINDS: tuple[str, ...] = ("skills", "agents", "hooks")

# Plugin names become dist/ path components; reject traversal or separators.
_SAFE_PLUGIN_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


PluginIndex = dict[str, dict[str, list[str]]]


def _empty_index() -> PluginIndex:
    return {kind: {} for kind in KINDS}


def build_plugin_index(root: Path) -> PluginIndex:
    """Read all `src/plugins/*/plugin.yaml` files into a reverse index.

    Returns a dict keyed by kind (`skills`, `agents`, `hooks`); each value
    maps artifact name to the list of plugin names that own it (sorted,
    deduplicated). Plugins with no `plugin.yaml` are skipped silently;
    plugins that omit a kind contribute nothing for that kind.
    """
    index = _empty_index()
    plugins_root = root / "src" / "plugins"
    if not plugins_root.is_dir():
        return index

    for plugin_dir in sorted(p for p in plugins_root.iterdir() if p.is_dir()):
        manifest = plugin_dir / "plugin.yaml"
        if not manifest.is_file():
            continue
        try:
            data = yaml.safe_load(manifest.read_text()) or {}
        except yaml.YAMLError as exc:
            raise ValueError(f"{manifest}: invalid YAML: {exc}") from exc
        if not isinstance(data, Mapping):
            raise ValueError(f"{manifest}: top-level must be a mapping")
        plugin_name = data.get("name") or plugin_dir.name
        if not _SAFE_PLUGIN_NAME_RE.match(str(plugin_name)):
            raise ValueError(
                f"{manifest}: plugin name {plugin_name!r} contains unsafe characters"
            )
        for kind in KINDS:
            names = data.get(kind) or []
            if not isinstance(names, list):
                raise ValueError(
                    f"{manifest}: {kind!r} must be a list, got {type(names).__name__}"
                )
            for name in names:
                if not isinstance(name, str):
                    raise ValueError(
                        f"{manifest}: {kind!r} entries must be strings; got {name!r}"
                    )
                owners = index[kind].setdefault(name, [])
                if plugin_name not in owners:
                    owners.append(plugin_name)

    for kind in KINDS:
        for owners in index[kind].values():
            owners.sort()

    return index


def validate_artifacts_exist(root: Path, index: PluginIndex) -> None:
    """Fail fast when a `plugin.yaml` references a missing source directory.

    Kept separate from `build_plugin_index` so tests can construct a
    synthetic index without needing matching `src/<kind>/<name>/` trees.
    """
    src = root / "src"
    missing: list[str] = []
    for kind, mapping in index.items():
        src_dir = src / kind
        for name, owners_list in mapping.items():
            if not (src_dir / name).is_dir():
                owners_str = ", ".join(owners_list)
                missing.append(f"{kind}/{name} (referenced by {owners_str})")
    if missing:
        raise ValueError(
            "plugin.yaml references missing source(s):\n  - " + "\n  - ".join(missing)
        )


_PLUGIN_GROUPED_TARGETS: frozenset[str] = frozenset({"claude", "codex"})


def _layout_for(target: str, kind: str) -> str:
    """Return the dist layout (`plugin` or `flat`) for a target+kind pair.

    Targets can override the layout per artifact kind via `agent_layout`,
    `skill_layout`, or `hook_layout` in `compile.OUTPUT`. Falls back to the
    target's top-level `layout` when no override is set. Used both for path
    resolution and ownership validation so the two stay aligned.
    """
    cfg = _compile.OUTPUT[target]
    _override_keys = {
        "skills": "skill_layout",
        "agents": "agent_layout",
        "hooks": "hook_layout",
    }
    override_key = _override_keys[kind]
    return cfg.get(override_key, cfg["layout"])


def _plugin_grouped_targets_for_kind(kind: str) -> frozenset[str]:
    """Return targets that use plugin grouping for the given artifact kind.

    Honors per-kind layout overrides so a target that emits, say, agents
    flat is not counted as plugin-grouped for ownership purposes.
    """
    return frozenset(
        t for t in _PLUGIN_GROUPED_TARGETS if _layout_for(t, kind) == "plugin"
    )


def _base_targets(base_path: Path) -> list[str] | None:
    """Return the `targets:` restriction from a base SKILL/AGENT, or None.

    Returns None when the file has no `targets:` key (meaning all targets
    are allowed). Returns a list of target names otherwise. String values
    are normalized to a one-element list.
    """
    if not base_path.is_file():
        return None
    meta = frontmatter.loads(base_path.read_text()).metadata
    if not isinstance(meta, Mapping):
        return None
    raw = meta.get("targets")
    if raw is None:
        return None
    if isinstance(raw, str):
        return [raw]
    if not isinstance(raw, list):
        return None
    out: list[str] = []
    for t in raw:  # type: ignore[union-attr]
        out.append(str(t))
    return out


def validate_plugin_ownership(root: Path, index: PluginIndex) -> None:
    """Fail when a source artifact lands on no plugin-grouped target.

    For each skill/agent under `src/`: if its base `targets:` allows any
    plugin-grouped target (`claude`, `codex`) and yet no `plugin.yaml`
    lists it, the build would emit no output for those targets. That hides
    misconfigurations (a new skill added to `src/skills/` but forgotten in
    `plugin.yaml`), so refuse to proceed.

    Artifacts restricted to flat-only targets (`pi`, `gemini`) are
    exempt — they intentionally bypass plugin grouping.
    """
    src = root / "src"
    base_files = {"skills": "SKILL.md", "agents": "AGENT.md"}
    missing: list[str] = []
    for kind, base_name in base_files.items():
        kind_dir = src / kind
        if not kind_dir.is_dir():
            continue
        owners_map = index.get(kind, {})
        grouped = _plugin_grouped_targets_for_kind(kind)
        if not grouped:
            # All plugin-capable targets emit this kind flat; ownership is
            # informational only. Skip the existence check entirely.
            continue
        for item in sorted(p for p in kind_dir.iterdir() if p.is_dir()):
            if owners_map.get(item.name):
                continue
            targets = _base_targets(item / base_name)
            if targets is not None and not (grouped & set(targets)):
                continue
            missing.append(f"{kind}/{item.name}")
    if missing:
        raise ValueError(
            "source artifact(s) not owned by any plugin.yaml; add them or "
            "restrict their `targets:` to pi/gemini:\n  - " + "\n  - ".join(missing)
        )


def owners(
    name: str,
    kind: str,
    plugin_index: PluginIndex | None,
) -> list[str]:
    """Return the plugin names that own `name` for `kind`.

    Empty list when the artifact is not listed in any `plugin.yaml`.
    """
    if kind not in KINDS:
        raise ValueError(f"unknown kind {kind!r}; expected one of {KINDS}")
    if not plugin_index:
        return []
    return list(plugin_index.get(kind, {}).get(name, []))


def output_paths(
    name: str,
    kind: str,
    target: str,
    plugin_index: PluginIndex | None,
    root: Path,
) -> list[Path]:
    """Resolve dist output directories for `name` of `kind` for `target`.

    Plugin-grouped targets (`layout: plugin`) emit one directory per owning
    plugin; an unowned artifact returns an empty list (skipped). Flat
    targets always return the single flat directory.

    The returned paths are *directories* — callers append `<name>/SKILL.md`
    (skills), `<name>.md` / `<name>.toml` (agents), or `<script>` (hooks)
    as appropriate.
    """
    if kind not in KINDS:
        raise ValueError(f"unknown kind {kind!r}; expected one of {KINDS}")
    if target not in _compile.OUTPUT:
        raise ValueError(f"unknown target {target!r}")
    cfg = _compile.OUTPUT[target]
    dir_key = {"skills": "skill_dir", "agents": "agent_dir", "hooks": "hook_dir"}[kind]
    dist = root / "dist" / target
    leaf = cfg[dir_key]
    if _layout_for(target, kind) == "plugin":
        plugins = owners(name, kind, plugin_index)
        if not plugins:
            return []
        return [dist / "plugins" / p / leaf for p in plugins]
    return [dist / leaf]
