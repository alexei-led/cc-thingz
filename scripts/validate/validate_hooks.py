#!/usr/bin/env python3
"""Validate generated hook registrations for every agent target.

Checks each rendered hook config under `dist/`:

- the file parses and has the target's shape;
- every event name is one the target runtime knows;
- matchers compile, timeouts are positive, handlers are commands;
- every packaged file a command runs exists inside the plugin, and the command
  uses the plugin-root variable that target expands.

Runtime execution of the same commands lives in `tests/test_validate_hooks.py`.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# Matches `${VAR}` or `$VAR` followed, possibly across shell quotes, by a path.
ROOTED_REFERENCE = re.compile(
    r"\$\{?(?P<var>[A-Z][A-Z0-9_]*)\}?[\"']*(?P<path>/[\w./-]+)"
)
# Matches `./path` not preceded by a path character (Cursor plugin-relative).
RELATIVE_REFERENCE = re.compile(r"(?<![\w./])\./(?P<path>[\w./-]+)")


@dataclass(frozen=True)
class TargetSpec:
    config_glob: str
    events: frozenset[str]
    root_variable: str | None
    grouped: bool
    command_key: str
    timeout_key: str


CLAUDE_EVENTS = frozenset(
    {
        "PreToolUse",
        "PostToolUse",
        "PostToolUseFailure",
        "PermissionRequest",
        "Notification",
        "UserPromptSubmit",
        "Stop",
        "SubagentStart",
        "SubagentStop",
        "PreCompact",
        "SessionStart",
        "SessionEnd",
    }
)

TARGETS: dict[str, TargetSpec] = {
    "claude": TargetSpec(
        "*/hooks/hooks.json",
        CLAUDE_EVENTS,
        "CLAUDE_PLUGIN_ROOT",
        True,
        "command",
        "timeout",
    ),
    "codex": TargetSpec(
        "*/hooks/hooks.json",
        frozenset(
            {
                "PreToolUse",
                "PermissionRequest",
                "PostToolUse",
                "PreCompact",
                "PostCompact",
                "SessionStart",
                "SessionEnd",
                "UserPromptSubmit",
                "SubagentStart",
                "SubagentStop",
                "Stop",
            }
        ),
        "PLUGIN_ROOT",
        True,
        "command",
        "timeout",
    ),
    "copilot": TargetSpec(
        "*/hooks.json",
        frozenset(
            {
                "SessionStart",
                "SessionEnd",
                "UserPromptSubmit",
                "PreToolUse",
                "PostToolUse",
                "Stop",
                "SubagentStop",
                "Notification",
                "PreCompact",
            }
        ),
        "PLUGIN_ROOT",
        False,
        "bash",
        "timeoutSec",
    ),
    "cursor": TargetSpec(
        "*/hooks/hooks.json",
        frozenset(
            {
                "sessionStart",
                "sessionEnd",
                "preToolUse",
                "postToolUse",
                "postToolUseFailure",
                "subagentStart",
                "subagentStop",
                "beforeShellExecution",
                "afterShellExecution",
                "beforeMCPExecution",
                "afterMCPExecution",
                "beforeReadFile",
                "afterFileEdit",
                "beforeSubmitPrompt",
                "preCompact",
                "stop",
                "afterAgentResponse",
                "afterAgentThought",
            }
        ),
        None,
        False,
        "command",
        "timeout",
    ),
    "grok": TargetSpec(
        "*/hooks/hooks.json",
        CLAUDE_EVENTS,
        "GROK_PLUGIN_ROOT",
        True,
        "command",
        "timeout",
    ),
}

PI_PORTABLE_EVENTS = frozenset(
    {"session-start", "prompt-submit", "pre-tool", "post-tool", "stop"}
)
PI_COMPATIBILITY_EVENTS = CLAUDE_EVENTS
PI_PROGRAMS = frozenset({"bash", "python3", "node", "sh"})


def iter_hook_configs(dist: Path) -> Iterator[tuple[str, Path, Path]]:
    """Yield (target, plugin root, config path) for every rendered vendor config."""
    for target, spec in TARGETS.items():
        for config in sorted((dist / target).glob(spec.config_glob)):
            plugin_root = (
                config.parent.parent if config.parent.name == "hooks" else config.parent
            )
            yield target, plugin_root, config


def _load(path: Path, errors: list[str]) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        errors.append(f"{path}: unreadable JSON: {error}")
        return None
    if not isinstance(data, dict) or not isinstance(data.get("hooks"), dict):
        errors.append(f"{path}: expected an object with a 'hooks' object")
        return None
    return data


def _handlers(
    spec: TargetSpec, groups: object, where: str, errors: list[str]
) -> Iterator[tuple[dict, str | None]]:
    if not isinstance(groups, list) or not groups:
        errors.append(f"{where}: expected a non-empty list")
        return
    for index, group in enumerate(groups):
        if not isinstance(group, dict):
            errors.append(f"{where}[{index}]: expected an object")
            continue
        if not spec.grouped:
            yield group, group.get("matcher")
            continue
        handlers = group.get("hooks")
        if not isinstance(handlers, list) or not handlers:
            errors.append(f"{where}[{index}]: expected a non-empty 'hooks' list")
            continue
        for handler in handlers:
            if not isinstance(handler, dict):
                errors.append(f"{where}[{index}]: handler must be an object")
                continue
            yield handler, group.get("matcher")


def command_references(
    text: str, root_variable: str | None
) -> tuple[list[str], list[str]]:
    """Return (plugin-relative paths, foreign root variables) a command uses."""
    paths: list[str] = []
    foreign: list[str] = []
    for match in ROOTED_REFERENCE.finditer(text):
        variable = match["var"]
        if variable == root_variable:
            paths.append(match["path"].lstrip("/"))
        elif variable.endswith("PLUGIN_ROOT"):
            foreign.append(variable)
    if root_variable is None:
        paths.extend(match["path"] for match in RELATIVE_REFERENCE.finditer(text))
    return paths, foreign


def _check_references(
    texts: list[str],
    root_variable: str | None,
    base: Path,
    where: str,
    errors: list[str],
    *,
    require: bool,
) -> None:
    text = "\n".join(texts)
    paths, foreign = command_references(text, root_variable)
    expected = f"${{{root_variable}}}" if root_variable else "plugin-relative ./ paths"
    for variable in sorted(set(foreign)):
        errors.append(f"{where}: uses ${{{variable}}}; this target expands {expected}")
    if require and not paths:
        errors.append(f"{where}: command does not run a packaged file")
    for relative in paths:
        target = (base / relative).resolve()
        if not target.is_relative_to(base.resolve()):
            errors.append(f"{where}: {relative} escapes the plugin root")
        elif not target.is_file():
            errors.append(f"{where}: missing referenced file {base / relative}")


def validate_config(target: str, plugin_root: Path, config: Path) -> list[str]:
    """Validate one vendor hook config and return human-readable errors."""
    spec = TARGETS[target]
    errors: list[str] = []
    data = _load(config, errors)
    if data is None:
        return errors
    for event, groups in data["hooks"].items():
        where = f"{config}: {event}"
        if event not in spec.events:
            errors.append(f"{where}: unknown {target} hook event")
        for handler, matcher in _handlers(spec, groups, where, errors):
            if matcher is not None:
                try:
                    re.compile(matcher)
                except (re.error, TypeError):
                    errors.append(f"{where}: invalid matcher {matcher!r}")
            if handler.get("type", "command") != "command":
                errors.append(f"{where}: unsupported handler type {handler['type']!r}")
            command = handler.get(spec.command_key)
            if not isinstance(command, str) or not command.strip():
                errors.append(f"{where}: missing '{spec.command_key}' string")
                continue
            timeout = handler.get(spec.timeout_key)
            if timeout is not None and (
                isinstance(timeout, bool)
                or not isinstance(timeout, int | float)
                or timeout <= 0
            ):
                errors.append(f"{where}: {spec.timeout_key} must be a positive number")
            args = handler.get("args", [])
            if not isinstance(args, list) or not all(
                isinstance(arg, str) for arg in args
            ):
                errors.append(f"{where}: args must be a list of strings")
                args = []
            _check_references(
                [command, *args],
                spec.root_variable,
                plugin_root,
                where,
                errors,
                require=True,
            )
    return errors


def validate_pi(pi_root: Path) -> list[str]:
    """Validate the Pi portable manifest and compatibility hook config."""
    errors: list[str] = []
    manifest_path = pi_root / "hooks/hooks.v1.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        entries = manifest["hooks"]
        if not isinstance(entries, list):
            raise TypeError("hooks must be a list")
    except (OSError, ValueError, KeyError, TypeError) as error:
        errors.append(f"{manifest_path}: invalid portable manifest: {error}")
        entries = []
    identities: set[str] = set()
    for index, entry in enumerate(entries):
        where = f"{manifest_path}: hooks[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{where}: expected an object")
            continue
        identity = entry.get("identity")
        where = f"{manifest_path}: {identity or f'hooks[{index}]'}"
        if not isinstance(identity, str) or identity in identities:
            errors.append(f"{where}: missing or duplicate identity")
        identities.add(identity)
        if entry.get("event") not in PI_PORTABLE_EVENTS:
            errors.append(f"{where}: unknown portable event {entry.get('event')!r}")
        timeout = entry.get("timeoutMilliseconds")
        if not isinstance(timeout, int) or isinstance(timeout, bool) or timeout <= 0:
            errors.append(f"{where}: timeoutMilliseconds must be a positive integer")
        handler = entry.get("handler")
        if not isinstance(handler, dict) or handler.get("program") not in PI_PROGRAMS:
            errors.append(
                f"{where}: handler program must be one of {sorted(PI_PROGRAMS)}"
            )
            continue
        files = [
            argument["packageFile"]
            for argument in handler.get("arguments", [])
            if isinstance(argument, dict) and "packageFile" in argument
        ]
        if not files:
            errors.append(f"{where}: handler does not run a packaged file")
        for relative in files:
            if not (pi_root / relative).is_file():
                errors.append(f"{where}: missing referenced file {pi_root / relative}")

    compatibility = pi_root / "extensions/hooks.json"
    data = _load(compatibility, errors)
    if data is not None:
        spec = TargetSpec(
            "", PI_COMPATIBILITY_EVENTS, "PI_HOOKS_DIR", True, "command", "timeout"
        )
        for event, groups in data["hooks"].items():
            where = f"{compatibility}: {event}"
            if event not in spec.events:
                errors.append(f"{where}: unknown Pi compatibility hook event")
            for handler, _ in _handlers(spec, groups, where, errors):
                command = handler.get("command")
                if not isinstance(command, str) or not command.strip():
                    errors.append(f"{where}: missing 'command' string")
                    continue
                # External commands such as `ccgram hook` carry no packaged path.
                _check_references(
                    [command],
                    "PI_HOOKS_DIR",
                    pi_root / "hooks",
                    where,
                    errors,
                    require=False,
                )
    return errors


def validate_dist(dist: Path) -> list[str]:
    """Validate every generated hook config under `dist`."""
    errors: list[str] = []
    seen = 0
    for target, plugin_root, config in iter_hook_configs(dist):
        seen += 1
        errors.extend(validate_config(target, plugin_root, config))
    if seen == 0:
        errors.append(f"{dist}: no generated hook configs found")
    if (dist / "pi").is_dir():
        errors.extend(validate_pi(dist / "pi"))
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dist", type=Path, default=REPO_ROOT / "dist")
    args = parser.parse_args(argv)
    errors = validate_dist(args.dist)
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    if errors:
        return 1
    print("hook configs: all registrations reference existing packaged files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
