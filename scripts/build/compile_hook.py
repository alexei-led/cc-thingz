"""Per-target hook compilation pipeline.

Reads a `src/hooks/<name>/` source tree (a `HOOK.{sh,py}` script plus
`meta.yaml` and optional support dirs), copies the script and support files
to the per-target `dist/` location, and contributes to an aggregated event
manifest for that target.

Per-target output shape:

- claude: scripts copied to `dist/claude/plugins/<plugin>/hooks/<script>`.
  Per-plugin manifest `dist/claude/plugins/<plugin>/hooks/hooks.json`
  with `${CLAUDE_PLUGIN_ROOT}/hooks/<script>` substitution.
- codex:  scripts copied to `dist/codex/plugins/<plugin>/hooks/<script>`.
  Per-plugin manifest `dist/codex/plugins/<plugin>/hooks/codex.hooks.json`
  with `$PLUGIN_ROOT/hooks/<script>` substitution.
- gemini: scripts copied to `dist/gemini/hooks/<script>` (flat). One
  aggregated manifest `dist/gemini/hooks/hooks.json` with
  `${extensionPath}/hooks/<script>` substitution.
- pi:     scripts copied to `dist/pi/hooks/<script>` (flat). One generated
  manifest `dist/pi/extensions/hooks.json` merged with external Pi entries.

Hooks not owned by any plugin in `src/plugins/*/plugin.yaml` land at the flat
hook path even for plugin-grouped targets (`claude`, `codex`). This matches
`compile_skill`/`compile_agent` and lets vendor-neutral hooks remain reachable
when they have no plugin assignment.
"""

from __future__ import annotations

import json
import logging
import re
import shutil
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import yaml

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import compile as _compile  # noqa: E402

log = logging.getLogger("compile.hook")


# Source-event → per-target (event_name, matcher) mapping.
# `None` for a target = hook is skipped for that target's manifest (script
# files are still copied so settings.json / other consumers can reference
# them out-of-band).
EVENT_MAP: dict[str, dict[str, tuple[str, str | None] | None]] = {
    "sessionstart": {
        "claude": ("SessionStart", None),
        "gemini": ("SessionStart", None),
        "codex": ("SessionStart", None),
        "pi": ("SessionStart", None),
    },
    "preedit": {
        "claude": ("PreToolUse", "Write|Edit|MultiEdit"),
        "gemini": ("BeforeTool", "write_file|replace"),
        "codex": ("PreToolUse", "^apply_patch$"),
        "pi": ("PreToolUse", "Write|Edit|MultiEdit"),
    },
    "prebash": {
        "claude": ("PreToolUse", "Bash"),
        "gemini": ("BeforeTool", "run_shell_command"),
        "codex": ("PreToolUse", "^Bash$"),
        "pi": ("PreToolUse", "Bash"),
    },
    "postedit": {
        "claude": ("PostToolUse", "Write|Edit|MultiEdit"),
        "gemini": ("AfterTool", "write_file|replace"),
        "codex": ("PostToolUse", "^apply_patch$"),
        "pi": ("PostToolUse", "Write|Edit|MultiEdit"),
    },
    "posttool": {
        "claude": ("PostToolUse", None),
        "gemini": ("AfterTool", None),
        "codex": ("PostToolUse", None),
        "pi": ("PostToolUse", None),
    },
    "agentstop": {
        "claude": ("Stop", None),
        "gemini": ("AfterAgent", None),
        "codex": ("Stop", None),
        "pi": ("Stop", None),
    },
    "userpromptsubmit": {
        "claude": ("UserPromptSubmit", None),
        "gemini": ("BeforeAgent", None),
        "codex": None,
        "pi": ("UserPromptSubmit", None),
    },
    "notification": {
        "claude": ("Notification", None),
        "gemini": ("Notification", None),
        "codex": None,
        "pi": ("Notification", None),
    },
    "exitplanmode": {
        "claude": ("PreToolUse", "ExitPlanMode"),
        "gemini": None,
        "codex": None,
        "pi": ("PreToolUse", "ExitPlanMode"),
    },
    "worktreecreate": {
        "claude": ("WorktreeCreate", None),
        "gemini": None,
        "codex": None,
        "pi": None,
    },
    "worktreeremove": {
        "claude": ("WorktreeRemove", None),
        "gemini": None,
        "codex": None,
        "pi": None,
    },
}

GEMINI_SEQUENTIAL: frozenset[str] = frozenset({"BeforeTool", "AfterTool"})
GEMINI_EVENT_ORDER: tuple[str, ...] = (
    "BeforeTool",
    "AfterTool",
    "SessionStart",
    "BeforeAgent",
    "AfterAgent",
    "Notification",
)
CODEX_EVENT_ORDER: tuple[str, ...] = (
    "PreToolUse",
    "PostToolUse",
    "Stop",
    "SessionStart",
)
CLAUDE_EVENT_ORDER: tuple[str, ...] = (
    "Setup",
    "SessionStart",
    "UserPromptSubmit",
    "PreToolUse",
    "PostToolUse",
    "Notification",
    "Stop",
    "SubagentStop",
    "SessionEnd",
    "WorktreeCreate",
    "WorktreeRemove",
)
PI_EVENT_ORDER: tuple[str, ...] = (
    "SessionStart",
    "SessionEnd",
    "SubagentStart",
    "SubagentStop",
    "UserPromptSubmit",
    "PreToolUse",
    "PostToolUse",
    "Stop",
    "Notification",
)

_TARGET_SUBDIRS: frozenset[str] = frozenset(_compile.TARGETS)

# Hook names land directly in output paths, manifest entries, and command
# substitutions. Anything outside this character class would either escape the
# hooks directory (`../`) or break manifest JSON.
_SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")


@dataclass(frozen=True)
class HookSpec:
    """Parsed metadata + script reference for a single source hook."""

    name: str
    event: str
    timeout: int
    script_path: Path
    status_message: str | None = None
    targets: list[str] | None = None
    pi_async: bool = False
    pi_timeout: int | None = None

    @property
    def script_basename(self) -> str:
        """Output script filename (`<name>.<ext>` from the source extension)."""
        return f"{self.name}{self.script_path.suffix}"

    @property
    def effective_pi_timeout(self) -> int:
        return self.pi_timeout if self.pi_timeout is not None else self.timeout


@dataclass
class HookCompileResult:
    """Outcome of compiling one hook for one target.

    `placements` records the (output script path, owning plugin) tuples so the
    manifest builder knows where each script lives and which Codex plugin it
    belongs to. `plugin` is `None` for hooks emitted to a flat layout path.
    """

    spec: HookSpec
    placements: list[tuple[Path, str | None]] = field(default_factory=list)


def load_hook(hook_dir: Path) -> HookSpec:
    """Parse `meta.yaml` and resolve the lone `hook.*` script in `hook_dir`."""
    meta_path = hook_dir / "meta.yaml"
    if not meta_path.is_file():
        raise FileNotFoundError(f"missing meta.yaml in {hook_dir}")
    meta = yaml.safe_load(meta_path.read_text()) or {}

    scripts = sorted(p for p in hook_dir.glob("hook.*") if p.is_file())
    if not scripts:
        raise FileNotFoundError(f"no hook.* script in {hook_dir}")
    if len(scripts) > 1:
        raise ValueError(
            f"multiple hook.* scripts in {hook_dir}: {[s.name for s in scripts]}"
        )

    for field_name in ("name", "event", "timeout"):
        if field_name not in meta:
            raise ValueError(f"{meta_path}: missing required field {field_name!r}")

    event = meta["event"]
    if event not in EVENT_MAP:
        raise ValueError(
            f"{meta_path}: unknown event {event!r}; valid: {sorted(EVENT_MAP)}"
        )

    name = meta["name"]
    if not isinstance(name, str) or not _SAFE_NAME_RE.match(name):
        raise ValueError(
            f"{meta_path}: name {name!r} must match {_SAFE_NAME_RE.pattern}"
        )

    targets = meta.get("targets")
    if targets is not None:
        targets_valid = isinstance(targets, list) and all(
            isinstance(t, str) for t in targets
        )
        if not targets_valid:
            raise ValueError(f"{meta_path}: targets must be a list of target names")
        unknown = sorted(set(targets) - set(_compile.TARGETS))
        if unknown:
            raise ValueError(f"{meta_path}: unknown targets: {unknown}")

    pi_block = meta.get("pi")
    pi_async = False
    pi_timeout: int | None = None
    if pi_block is not None:
        if not isinstance(pi_block, dict):
            raise ValueError(f"{meta_path}: pi must be a mapping when present")
        if "async" in pi_block:
            if not isinstance(pi_block["async"], bool):
                raise ValueError(f"{meta_path}: pi.async must be a boolean")
            pi_async = pi_block["async"]
        if "timeout" in pi_block:
            if not isinstance(pi_block["timeout"], int) or pi_block["timeout"] <= 0:
                raise ValueError(f"{meta_path}: pi.timeout must be a positive integer")
            pi_timeout = pi_block["timeout"]

    return HookSpec(
        name=name,
        event=event,
        timeout=int(meta["timeout"]),
        script_path=scripts[0],
        status_message=meta.get("status_message"),
        targets=targets,
        pi_async=pi_async,
        pi_timeout=pi_timeout,
    )


def hook_output_assignments(
    name: str,
    target: str,
    plugin_index: Mapping[str, list[str]] | None,
    root: Path,
) -> list[tuple[Path, str | None]]:
    """Resolve per-target hook directories paired with their owning plugin.

    Plugin-grouped targets emit once per owning plugin; an unowned hook on a
    plugin-grouped target falls back to the flat path so the script is still
    available out-of-band (e.g. referenced from `.claude/settings.json`).
    Flat targets always use the flat path.
    """
    cfg = _compile.OUTPUT[target]
    dist = root / "dist" / target
    hook_dir = cfg["hook_dir"]
    if cfg["layout"] == "plugin":
        plugins = list((plugin_index or {}).get(name, []))
        if plugins:
            return [(dist / "plugins" / p / hook_dir, p) for p in plugins]
    return [(dist / hook_dir, None)]


def _copy_script(src: Path, dest: Path) -> None:
    """Copy `src` to `dest`, creating parents and preserving file mode."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dest)
    dest.chmod(src.stat().st_mode)


_SUPPORT_IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store")


def _copy_support_dirs(hook_dir: Path, out_dir: Path) -> None:
    """Copy any non-target sibling directories (support files) into `out_dir`."""
    for child in hook_dir.iterdir():
        if not child.is_dir():
            continue
        if child.name in _TARGET_SUBDIRS:
            continue
        if child.name == "__pycache__":
            continue
        shutil.copytree(
            child, out_dir / child.name, dirs_exist_ok=True, ignore=_SUPPORT_IGNORE
        )


def compile_hook(
    hook_dir: Path,
    target: str,
    plugin_index: Mapping[str, list[str]] | None,
    root: Path,
) -> HookCompileResult:
    """Place the hook's script + support files at every resolved output path."""
    spec = load_hook(hook_dir)
    result = HookCompileResult(spec=spec)
    if spec.targets is not None and target not in spec.targets:
        log.debug(
            "hook=%s target=%s skipped (not in targets:%s)",
            spec.name,
            target,
            spec.targets,
        )
        return result
    for out_dir, plugin in hook_output_assignments(
        spec.name, target, plugin_index, root
    ):
        dest = out_dir / spec.script_basename
        _copy_script(spec.script_path, dest)
        _copy_support_dirs(hook_dir, out_dir)
        result.placements.append((dest, plugin))
    return result


def _gemini_hook_entry(spec: HookSpec) -> dict:
    return {
        "type": "command",
        "name": spec.name,
        "command": f"${{extensionPath}}/hooks/{spec.script_basename}",
        "timeout": spec.timeout * 1000,
    }


def _codex_hook_entry(spec: HookSpec) -> dict:
    entry: dict = {
        "type": "command",
        "command": f'"$PLUGIN_ROOT/hooks/{spec.script_basename}"',
        "timeout": spec.timeout,
    }
    if spec.status_message:
        entry["statusMessage"] = spec.status_message
    return entry


def _claude_hook_entry(spec: HookSpec) -> dict:
    return {
        "type": "command",
        "command": f"${{CLAUDE_PLUGIN_ROOT}}/hooks/{spec.script_basename}",
        "timeout": spec.timeout,
    }


def _to_bytes(data: dict) -> bytes:
    return (json.dumps(data, indent=2) + "\n").encode()


def _build_gemini(specs: Sequence[HookSpec]) -> dict:
    groups: dict[tuple[str, str | None], list[dict]] = {}
    for spec in specs:
        mapping = EVENT_MAP[spec.event].get("gemini")
        if mapping is None:
            continue
        event_name, matcher = mapping
        key = (event_name, matcher)
        groups.setdefault(key, []).append(_gemini_hook_entry(spec))

    events: dict[str, list] = {}
    for event_name in GEMINI_EVENT_ORDER:
        event_groups = []
        for (ev, matcher), hooks in groups.items():
            if ev != event_name:
                continue
            group: dict = {}
            if matcher is not None:
                group["matcher"] = matcher
            if ev in GEMINI_SEQUENTIAL:
                group["sequential"] = True
            group["hooks"] = hooks
            event_groups.append(group)
        if event_groups:
            events[event_name] = event_groups
    return {"hooks": events}


def _build_codex(specs: Sequence[HookSpec]) -> dict:
    groups: dict[tuple[str, str | None], list[dict]] = {}
    for spec in specs:
        mapping = EVENT_MAP[spec.event].get("codex")
        if mapping is None:
            continue
        event_name, matcher = mapping
        key = (event_name, matcher)
        groups.setdefault(key, []).append(_codex_hook_entry(spec))

    events: dict[str, list] = {}
    for event_name in CODEX_EVENT_ORDER:
        event_groups = []
        for (ev, matcher), hooks in groups.items():
            if ev != event_name:
                continue
            group: dict = {}
            if matcher is not None:
                group["matcher"] = matcher
            group["hooks"] = hooks
            event_groups.append(group)
        if event_groups:
            events[event_name] = event_groups
    return {"hooks": events}


def _pi_hook_entry(spec: HookSpec) -> dict:
    entry: dict = {
        "type": "command",
        "command": f"${{PI_HOOKS_DIR}}/{spec.script_basename}",
        "timeout": spec.effective_pi_timeout,
    }
    if spec.pi_async:
        entry["async"] = True
    return entry


def _build_pi(specs: Sequence[HookSpec], external: dict | None = None) -> dict:
    """Assemble Pi `hooks.json`.

    `external` is the optional `src/pi-extensions/hooks-external.json` content
    (third-party commands like `ccgram hook` that aren't owned by `src/hooks/`).
    External groups are merged in alongside meta.yaml-derived groups; both
    survive the build with no hand-maintained duplication.

    Fails loudly if any spec maps to a Pi event name absent from PI_EVENT_ORDER —
    silently dropping a hook from the manifest because the order list is stale
    has been a real source of "hook didn't fire and nobody noticed" bugs.
    """
    groups: dict[tuple[str, str | None], list[dict]] = {}
    for spec in specs:
        mapping = EVENT_MAP[spec.event].get("pi")
        if mapping is None:
            continue
        event_name, matcher = mapping
        if event_name not in PI_EVENT_ORDER:
            raise ValueError(
                f"hook {spec.name!r} maps to Pi event {event_name!r} which is "
                "not in PI_EVENT_ORDER; add it to scripts/build/compile_hook.py "
                "to emit a manifest entry"
            )
        key = (event_name, matcher)
        groups.setdefault(key, []).append(_pi_hook_entry(spec))

    events: dict[str, list] = {}
    for event_name in PI_EVENT_ORDER:
        event_groups = []
        for (ev, matcher), hooks in groups.items():
            if ev != event_name:
                continue
            group: dict = {}
            if matcher is not None:
                group["matcher"] = matcher
            group["hooks"] = hooks
            event_groups.append(group)
        if event_groups:
            events[event_name] = event_groups

    if external:
        external_hooks = external.get("hooks") if isinstance(external, dict) else None
        if isinstance(external_hooks, dict):
            # Merge is additive by design: identical (event, matcher) pairs from
            # external + meta.yaml both make it into the output. Pi's hook-runner
            # iterates groups in order, so duplicates run twice — let the
            # external manifest's author decide if that's intended rather than
            # second-guessing here.
            for event_name, ext_groups in external_hooks.items():
                if not isinstance(ext_groups, list):
                    continue
                events.setdefault(event_name, []).extend(ext_groups)

    return {"hooks": events}


def _build_claude(specs: Sequence[HookSpec]) -> dict:
    groups: dict[tuple[str, str | None], list[dict]] = {}
    for spec in specs:
        mapping = EVENT_MAP[spec.event].get("claude")
        if mapping is None:
            continue
        event_name, matcher = mapping
        key = (event_name, matcher)
        groups.setdefault(key, []).append(_claude_hook_entry(spec))

    events: dict[str, list] = {}
    for event_name in CLAUDE_EVENT_ORDER:
        event_groups = []
        for (ev, matcher), hooks in groups.items():
            if ev != event_name:
                continue
            group: dict = {}
            if matcher is not None:
                group["matcher"] = matcher
            group["hooks"] = hooks
            event_groups.append(group)
        if event_groups:
            events[event_name] = event_groups
    return {"hooks": events}


def write_hook_manifests(
    results: Sequence[HookCompileResult],
    target: str,
    root: Path,
) -> list[Path]:
    """Aggregate compiled hooks for `target` into per-target manifest files.

    Gemini receives a single `dist/gemini/hooks/hooks.json` covering every
    hook. Claude and Codex receive one manifest per owning plugin. Pi receives
    `dist/pi/extensions/hooks.json` merged from meta.yaml-derived entries and
    `scripts/build/pi-hooks-external.json` (third-party commands not owned by
    `src/hooks/` — sits next to the build script that reads it).
    """
    if not results:
        return []

    dist = root / "dist" / target
    written: list[Path] = []

    if target == "gemini":
        specs = [r.spec for r in results if r.placements]
        manifest = _build_gemini(specs)
        if manifest["hooks"]:
            path = dist / "hooks" / "hooks.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(_to_bytes(manifest))
            written.append(path)
        return written

    if target in {"claude", "codex"}:
        # Group specs by owning plugin; placements without a plugin land at the
        # flat fallback and get no manifest.
        by_plugin: dict[str, list[HookSpec]] = {}
        for result in results:
            for placement in result.placements:
                plugin = placement[1]
                if plugin is None:
                    continue
                by_plugin.setdefault(plugin, []).append(result.spec)
        for plugin, specs in by_plugin.items():
            if target == "claude":
                manifest = _build_claude(specs)
            else:
                manifest = _build_codex(specs)
            manifest_name = "hooks.json"
            if not manifest["hooks"]:
                continue
            path = dist / "plugins" / plugin / "hooks" / manifest_name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(_to_bytes(manifest))
            written.append(path)
        return written

    if target == "pi":
        specs = [r.spec for r in results if r.placements]
        external_path = root / "scripts" / "build" / "pi-hooks-external.json"
        external: dict | None = None
        if external_path.is_file():
            try:
                external = json.loads(external_path.read_text())
            except json.JSONDecodeError as exc:
                raise ValueError(f"{external_path}: invalid JSON ({exc})") from exc
        manifest = _build_pi(specs, external)
        if manifest["hooks"]:
            path = dist / "extensions" / "hooks.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(_to_bytes(manifest))
            written.append(path)
        return written

    return written
