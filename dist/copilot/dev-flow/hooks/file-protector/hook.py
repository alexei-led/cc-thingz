#!/usr/bin/env python3
"""PreToolUse hook — block writes to sensitive files.

Handles Claude Code and Codex single-file tool payloads and
patch-based tools (Codex apply_patch, which may touch multiple files per call).

Configuration (~/.claude/hook-config.json, fileProtector section):
  protectedPatterns  — list of regex strings; matched files are blocked (exit 2)
  lockFilePatterns   — list of regex strings; matched files emit a warning (exit 0)

Project-local configuration (nearest ancestor `.claude/file-protector.json`):
  excludePatterns    — regex strings exempted from the global protected patterns.
                       This file must be committed with the project and applies
                       only to absolute paths below its nearest project root.

Falls back to hardcoded defaults when the config file is absent or malformed.

Exit codes:
  0  allow
  2  block (stderr message forwarded to the agent)
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_CONFIG_FILE = Path.home() / ".claude" / "hook-config.json"
_PROJECT_CONFIG_NAME = ".claude/file-protector.json"

_DEFAULT_PROTECTED: list[str] = [
    r"\.env$",
    r"\.env\.",
    r"/\.env$",
    r"secrets/",
    r"secret[s]?\.",
    r"\.key$",
    r"\.pem$",
    r"\.p12$",
    r"\.pfx$",
    r"\.ssh/",
    r"id_rsa",
    r"id_ed25519",
    r"credentials",
    r"password",
    r"\.secret$",
    r"api[_-]?key",
    r"auth[_-]?token",
]

_DEFAULT_LOCKS: list[str] = [
    r"package-lock\.json$",
    r"yarn\.lock$",
    r"pnpm-lock\.yaml$",
    r"go\.sum$",
    r"Cargo\.lock$",
    r"poetry\.lock$",
    r"Gemfile\.lock$",
    r"composer\.lock$",
]

# Patch header patterns for apply_patch (Codex custom format + unified diff)
_PATCH_FILE_RE = re.compile(
    r"^\*\*\* (?:(?:Update|Add|Delete) File|Move to): (.+)$|^\+\+\+ b/(.+)$",
    re.MULTILINE,
)


def _load_patterns(section: str, default: list[str]) -> list[str]:
    if not _CONFIG_FILE.is_file():
        return default
    try:
        cfg = json.loads(_CONFIG_FILE.read_text())
        patterns = cfg.get("fileProtector", {}).get(section, None)
        return patterns if patterns is not None else default
    except (json.JSONDecodeError, OSError):
        return default


def _extract_patch_paths(patch: str) -> list[str]:
    """Extract all file paths touched by an apply_patch patch string."""
    paths = []
    for m in _PATCH_FILE_RE.finditer(patch):
        paths.append(m.group(1) or m.group(2))
    return paths


_warned_bad_patterns: set[str] = set()


def _safe_search(pattern: str, path: str) -> bool:
    """Match `path` against a user-supplied `pattern`, tolerating bad regexes.

    A malformed regex in ~/.claude/hook-config.json must not crash the hook
    on every edit — fail open for that one pattern (skip it, warn once per
    run) while the remaining valid patterns keep enforcing.
    """
    try:
        return re.search(pattern, path) is not None
    except re.error as exc:
        if pattern not in _warned_bad_patterns:
            _warned_bad_patterns.add(pattern)
            print(
                f"WARNING: Invalid regex pattern skipped: {pattern} ({exc})",
                file=sys.stderr,
            )
        return False


def _deny(path: str, pattern: str, pi_runtime: bool) -> None:
    message = f"Cannot modify sensitive file: {path} (matched {pattern})"
    if pi_runtime:
        print(json.dumps({"decision": "deny", "reason": message}))
        raise SystemExit(0)
    print(f"BLOCKED: {message}", file=sys.stderr)
    print(
        "To customize: edit ~/.claude/hook-config.json"
        " (fileProtector.protectedPatterns)",
        file=sys.stderr,
    )
    raise SystemExit(2)


def _project_excludes(path: str) -> list[str]:
    """Load excludes from the nearest project config, if the path is absolute."""
    candidate = Path(path).expanduser()
    if not candidate.is_absolute():
        return []
    for parent in (candidate.parent, *candidate.parents):
        config = parent / _PROJECT_CONFIG_NAME
        if not config.is_file():
            continue
        try:
            value = json.loads(config.read_text()).get("excludePatterns", [])
        except (json.JSONDecodeError, OSError):
            return []
        if isinstance(value, list) and all(isinstance(x, str) for x in value):
            return value
        return []
    return []


def _check_path(
    path: str,
    protected: list[str],
    locks: list[str],
    pi_runtime: bool,
) -> None:
    """Check one path and emit the Agent Bundler Pi decision when needed."""
    excludes = _project_excludes(path)
    for pattern in protected:
        if _safe_search(pattern, path) and not any(
            _safe_search(exclude, path) for exclude in excludes
        ):
            _deny(path, pattern, pi_runtime)

    for pattern in locks:
        if _safe_search(pattern, path):
            print(f"WARNING: Modifying lock file: {path}", file=sys.stderr)
            print(
                "Lock files should typically be auto-generated by package managers",
                file=sys.stderr,
            )
            return


def main() -> None:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        sys.exit(0)

    pi_runtime = payload.get("event") == "pre-tool" and isinstance(
        payload.get("piEvent"), dict
    )
    tool_input = (
        payload["piEvent"].get("input", {})
        if pi_runtime
        else payload.get("tool_input", {})
    )
    if not isinstance(tool_input, dict):
        tool_input = {}
    protected = _load_patterns("protectedPatterns", _DEFAULT_PROTECTED)
    locks = _load_patterns("lockFilePatterns", _DEFAULT_LOCKS)

    path = tool_input.get("file_path") or tool_input.get("path") or ""
    if path:
        _check_path(path, protected, locks, pi_runtime)
    else:
        patch = tool_input.get("patch") or ""
        for changed_path in _extract_patch_paths(patch):
            _check_path(changed_path, protected, locks, pi_runtime)

    if pi_runtime:
        print('{"decision":"allow"}')


if __name__ == "__main__":
    main()
