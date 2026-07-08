"""Root-level marketplace and extension manifest generators.

Reads `src/plugins/<plugin>/plugin.yaml` files plus optional top-level
metadata at `src/plugins/marketplace.yaml`, and writes the three manifest
files target consumers expect at the repo root:

- `.claude-plugin/marketplace.json` — Claude Code plugin marketplace,
  sources resolve to `./dist/claude/plugins/<plugin>`.
- `.agents/plugins/marketplace.json` — Codex CLI marketplace, sources
  resolve to `./dist/codex/plugins/<plugin>`.
- `gemini-extension.json` — single Gemini CLI extension manifest at
  repo root; companion content is found via root-level symlinks
  (`skills/`, `hooks/`) that point into `dist/gemini/`.

The module is intentionally tolerant of missing optional fields. Any
plugin manifest that declares extra metadata (category, tags, keywords,
author, homepage, repository, license) has it carried into the
generated marketplace entries; fields that are absent are omitted.

Top-level marketplace metadata (owner, repo, license, description,
version) is read from `src/plugins/marketplace.yaml` when present and
otherwise filled in with sensible defaults derived from the plugin
list.
"""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

import yaml

log = logging.getLogger("compile.manifests")


_GEMINI_SYMLINK_TARGETS: tuple[tuple[str, str], ...] = (
    ("skills", "dist/gemini/skills"),
    ("agents", "dist/gemini/agents"),
    ("hooks", "dist/gemini/hooks"),
)


def load_global_meta(root: Path) -> dict[str, Any]:
    """Read optional `src/plugins/marketplace.yaml` for shared manifest metadata.

    Returns an empty dict when the file is absent. The file may declare
    top-level fields (`name`, `owner`, `description`, `version`,
    `homepage`, `repository`, `license`) that get woven into the
    generated Claude marketplace manifest.
    """
    p = root / "src" / "plugins" / "marketplace.yaml"
    if not p.is_file():
        return {}
    data = yaml.safe_load(p.read_text()) or {}
    if not isinstance(data, Mapping):
        raise ValueError(f"{p}: top-level must be a mapping")
    return dict(data)


def load_plugins(root: Path) -> list[dict[str, Any]]:
    """Load every `src/plugins/<plugin>/plugin.yaml` into a sorted list.

    Each entry is the parsed dict with `name` defaulted to the directory
    name when omitted. Plugins without `plugin.yaml` are skipped. The
    return order is alphabetical by plugin directory name so generated
    manifests are deterministic.
    """
    plugins_root = root / "src" / "plugins"
    if not plugins_root.is_dir():
        return []
    out: list[dict[str, Any]] = []
    for plugin_dir in sorted(p for p in plugins_root.iterdir() if p.is_dir()):
        manifest = plugin_dir / "plugin.yaml"
        if not manifest.is_file():
            continue
        data = yaml.safe_load(manifest.read_text()) or {}
        if not isinstance(data, Mapping):
            raise ValueError(f"{manifest}: top-level must be a mapping")
        entry = dict(data)
        entry.setdefault("name", plugin_dir.name)
        out.append(entry)
    return out


def _copy_optional(
    src: Mapping[str, Any],
    dst: dict[str, Any],
    keys: Iterable[str],
) -> None:
    for k in keys:
        if k in src and src[k] is not None:
            dst[k] = src[k]


def _write_json(path: Path, data: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, indent=2, sort_keys=False) + "\n"
    path.write_text(payload)


def _resolve_version(
    global_meta: Mapping[str, Any],
    plugins: Sequence[Mapping[str, Any]],
) -> str:
    version = global_meta.get("version")
    if isinstance(version, str) and version:
        return version
    for p in plugins:
        v = p.get("version")
        if isinstance(v, str) and v:
            return v
    return "0.0.0"


def write_claude_marketplace(plugins: Sequence[Mapping[str, Any]], root: Path) -> Path:
    """Write `.claude-plugin/marketplace.json` with Claude-flavored entries.

    Each plugin entry's `source` resolves to `./dist/claude/plugins/<name>`
    so Claude Code reads compiled artifacts rather than the legacy
    `plugins/<name>/` source tree.
    """
    global_meta = load_global_meta(root)
    version = _resolve_version(global_meta, plugins)
    payload: dict[str, Any] = {
        "name": global_meta.get("name") or "cc-thingz",
    }
    owner = global_meta.get("owner")
    if isinstance(owner, Mapping):
        payload["owner"] = dict(owner)
    else:
        # validate-config.py treats owner as mandatory; surface the gap at
        # generation time instead of failing later in validation.
        log.warning(
            "marketplace.yaml has no 'owner' mapping; "
            "generated marketplace.json will fail validate-config.py"
        )

    metadata: dict[str, Any] = {}
    _copy_optional(
        global_meta,
        metadata,
        ("description", "homepage", "repository", "license"),
    )
    metadata["version"] = version
    if metadata:
        payload["metadata"] = metadata

    entries: list[dict[str, Any]] = []
    for plugin in plugins:
        name = plugin["name"]
        plugin_root = root / "dist" / "claude" / "plugins" / name
        if not plugin_root.is_dir():
            # plugin contributes no claude artifacts — omit from marketplace
            continue
        entry: dict[str, Any] = {
            "name": plugin.get("marketplace_name") or name,
            "source": f"./dist/claude/plugins/{name}",
        }
        _copy_optional(
            plugin,
            entry,
            (
                "description",
                "category",
                "tags",
                "version",
                "author",
                "homepage",
                "repository",
                "license",
                "keywords",
            ),
        )
        entry.setdefault("version", version)
        entries.append(entry)
    payload["plugins"] = entries
    payload["version"] = version

    out = root / ".claude-plugin" / "marketplace.json"
    _write_json(out, payload)
    log.info("wrote %s (%d plugin(s))", out.relative_to(root), len(entries))
    return out


def _plugin_manifest_payload(
    plugin: Mapping[str, Any],
    global_meta: Mapping[str, Any],
    fallback_version: str,
) -> dict[str, Any]:
    """Build a per-plugin manifest dict shared by Claude and Codex emitters.

    Plugin-level fields win; missing optional metadata (author/homepage/
    repository/license) falls back to the global marketplace metadata so
    consumers do not see anonymous plugins.
    """
    payload: dict[str, Any] = {
        "name": plugin["name"],
        "version": plugin.get("version") or fallback_version,
    }
    if plugin.get("description"):
        payload["description"] = plugin["description"]

    author = plugin.get("author")
    if author is None:
        owner = global_meta.get("owner")
        if isinstance(owner, Mapping):
            author = dict(owner)
    if author is not None:
        payload["author"] = author

    for key in ("homepage", "repository", "license"):
        if plugin.get(key) is not None:
            payload[key] = plugin[key]
        elif global_meta.get(key) is not None:
            payload[key] = global_meta[key]

    _copy_optional(plugin, payload, ("keywords", "category", "tags"))
    return payload


def write_claude_plugin_manifests(
    plugins: Sequence[Mapping[str, Any]], root: Path
) -> list[Path]:
    """Write `.claude-plugin/plugin.json` under each compiled Claude plugin dir.

    Each manifest enables Claude Code's `/plugin install <name>@<market>`
    flow once the marketplace entry is registered. Plugins without a
    `dist/claude/plugins/<name>/` directory are skipped.
    """
    global_meta = load_global_meta(root)
    version = _resolve_version(global_meta, plugins)
    written: list[Path] = []
    for plugin in plugins:
        name = plugin["name"]
        plugin_root = root / "dist" / "claude" / "plugins" / name
        if not plugin_root.is_dir():
            continue
        payload = _plugin_manifest_payload(plugin, global_meta, version)
        out = plugin_root / ".claude-plugin" / "plugin.json"
        _write_json(out, payload)
        written.append(out)
    log.info("wrote %d claude per-plugin manifest(s)", len(written))
    return written


def write_codex_plugin_manifests(
    plugins: Sequence[Mapping[str, Any]], root: Path
) -> list[Path]:
    """Write `.codex-plugin/plugin.json` under each compiled Codex plugin dir.

    Mirrors `write_claude_plugin_manifests` for Codex. When a plugin emits
    a hooks manifest (`hooks/hooks.json`), the relative path is referenced
    so Codex resolves it without scanning.
    """
    global_meta = load_global_meta(root)
    version = _resolve_version(global_meta, plugins)
    written: list[Path] = []
    for plugin in plugins:
        name = plugin["name"]
        plugin_root = root / "dist" / "codex" / "plugins" / name
        if not plugin_root.is_dir():
            continue
        payload = _plugin_manifest_payload(plugin, global_meta, version)
        # Use public_homepage/public_repository when set — the main homepage/
        # repository may point to a private enterprise repo for Claude Code.
        for key in ("homepage", "repository"):
            pub = global_meta.get(f"public_{key}")
            if pub and not plugin.get(key):
                payload[key] = pub
        if (plugin_root / "skills").is_dir():
            payload["skills"] = "./skills"
        hooks_manifest = plugin_root / "hooks" / "hooks.json"
        if hooks_manifest.is_file():
            payload["hooks"] = "./hooks/hooks.json"
        out = plugin_root / ".codex-plugin" / "plugin.json"
        _write_json(out, payload)
        written.append(out)
    log.info("wrote %d codex per-plugin manifest(s)", len(written))
    return written


def write_codex_marketplace(plugins: Sequence[Mapping[str, Any]], root: Path) -> Path:
    """Write `.agents/plugins/marketplace.json` with Codex-flavored entries.

    Codex expects `source: {source: "local", path: ...}` and a `policy`
    block per plugin. Sources resolve to `./dist/codex/plugins/<name>`.
    """
    global_meta = load_global_meta(root)
    payload: dict[str, Any] = {
        "name": global_meta.get("name") or "cc-thingz",
        "interface": {"displayName": global_meta.get("display_name") or "cc-thingz"},
    }
    entries: list[dict[str, Any]] = []
    for plugin in plugins:
        name = plugin["name"]
        plugin_root = root / "dist" / "codex" / "plugins" / name
        if not plugin_root.is_dir():
            # plugin contributes no codex artifacts — omit from marketplace
            continue
        entry: dict[str, Any] = {
            "name": plugin.get("marketplace_name") or name,
            "source": {
                "source": "local",
                "path": f"./dist/codex/plugins/{name}",
            },
            "policy": {
                "installation": "AVAILABLE",
                "authentication": "ON_USE",
            },
        }
        if "codex_category" in plugin:
            entry["category"] = plugin["codex_category"]
        elif "category" in plugin:
            entry["category"] = plugin["category"]
        entries.append(entry)
    payload["plugins"] = entries

    out = root / ".agents" / "plugins" / "marketplace.json"
    _write_json(out, payload)
    log.info("wrote %s (%d plugin(s))", out.relative_to(root), len(entries))
    return out


def write_gemini_extension(plugins: Sequence[Mapping[str, Any]], root: Path) -> Path:
    """Write the root `gemini-extension.json` manifest.

    Gemini's extension loader treats the repo root as the extension root
    and scans for hard-coded subdirs (`skills/`, `hooks/`) — those are
    created as symlinks by `ensure_gemini_symlinks`.
    """
    global_meta = load_global_meta(root)
    payload: dict[str, Any] = {
        "name": global_meta.get("name") or "cc-thingz",
        "version": _resolve_version(global_meta, list(plugins)),
        "description": global_meta.get("description")
        or (f"{len(plugins)} portable plugin(s) exported from cc-thingz"),
        "contextFileName": global_meta.get("context_file_name") or "AGENTS.md",
    }
    out = root / "gemini-extension.json"
    _write_json(out, payload)
    log.info("wrote %s", out.relative_to(root))
    return out


def ensure_gemini_symlinks(root: Path) -> list[Path]:
    """Create or refresh repo-root symlinks pointing into `dist/gemini/`.

    Idempotent: existing correct symlinks are left alone; stale symlinks
    (pointing somewhere else) are replaced; existing non-symlink paths
    of the same name raise an error rather than be clobbered.
    """
    created: list[Path] = []
    for name, target_rel in _GEMINI_SYMLINK_TARGETS:
        link = root / name
        target = Path(target_rel)

        if link.is_symlink():
            current = os.readlink(link)
            if current == target_rel:
                continue
            link.unlink()
        elif link.exists():
            raise FileExistsError(
                f"{link} exists and is not a symlink; refusing to clobber"
            )

        # Ensure the parent of the target exists so the symlink resolves.
        (root / target.parent).mkdir(parents=True, exist_ok=True)
        link.symlink_to(target)
        created.append(link)
        log.info("created symlink %s -> %s", link.relative_to(root), target_rel)
    return created


def write_all(root: Path) -> dict[str, Any]:
    """Write all root-level manifests and ensure Gemini symlinks exist."""
    plugins = load_plugins(root)
    return {
        "claude": write_claude_marketplace(plugins, root),
        "codex": write_codex_marketplace(plugins, root),
        "gemini": write_gemini_extension(plugins, root),
        "claude_plugins": write_claude_plugin_manifests(plugins, root),
        "codex_plugins": write_codex_plugin_manifests(plugins, root),
        "symlinks": ensure_gemini_symlinks(root),
    }
