#!/usr/bin/env python3
"""PreToolUse hook — block writes to sensitive files.

Handles Claude Code and Codex single-file tool payloads and
patch-based tools (Codex apply_patch, which may touch multiple files per call).

User policy: fileProtector in CLAUDE_HOOK_CONFIG or ~/.claude/hook-config.json.
Per-project profiles in the user policy can add protections and exempt exact
paths from built-in rules. Repository files cannot override explicit user rules.

Exit codes:
  0  allow
  2  block (stderr message forwarded to the agent)
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

_DEFAULT_WARN = [r"(?:^|/)\.env(?:rc|\.[^/]*)?$"]

_DEFAULT_PROTECTED = [
    r"(?:^|/)(?:secrets|\.ssh)/",
    r"\.(?:key|pem|p12|pfx|secret)$",
    r"(?:^|/)id_(?:rsa|ed25519|ecdsa|dsa)$",
    r"(?:^|/)(?:secret[s]?|(?:[\w-]+[_-])?(?:credentials|password)|"
    r"api[_-]?key|auth[_-]?token)(?:\.(?:txt|json|yaml|yml|conf|env|toml))?$",
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
    r"^\*\*\* (?:(?:Update|Add|Delete) File|Move to): (.+)$|^(?:--- a/|\+\+\+ b/)(.+)$",
    re.MULTILINE,
)


def _load_policy() -> tuple[Path, dict, dict]:
    config = Path(
        os.environ.get("CLAUDE_HOOK_CONFIG") or Path.home() / ".claude/hook-config.json"
    ).expanduser()
    try:
        decoded = json.loads(config.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return config, {}, {}
    except (ValueError, OSError) as exc:
        print(
            f"WARNING: Cannot read file-protector policy {config}: {exc}",
            file=sys.stderr,
        )
        return config, {}, {}
    policy = decoded.get("fileProtector") if isinstance(decoded, dict) else None
    projects = decoded.get("projects") if isinstance(decoded, dict) else None
    return (
        config,
        policy if isinstance(policy, dict) else {},
        projects if isinstance(projects, dict) else {},
    )


def _patterns(policy: dict, field: str, default: list[str]) -> list[str]:
    value = policy.get(field)
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return value
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


def _deny(path: str, rule: str, pi_runtime: bool) -> None:
    message = f"Cannot modify sensitive file: {path} ({rule})"
    if pi_runtime:
        print(json.dumps({"decision": "deny", "reason": message}))
        raise SystemExit(0)
    print(f"BLOCKED: {message}", file=sys.stderr)
    print(
        "To customize: edit fileProtector in your user hook-config.json",
        file=sys.stderr,
    )
    raise SystemExit(2)


def _project_policy(projects: dict, cwd: Path) -> tuple[Path, dict | None]:
    for root in (cwd, *cwd.parents):
        entry = projects.get(str(root))
        if isinstance(entry, dict) and isinstance(entry.get("fileProtector"), dict):
            return root, entry["fileProtector"]
    return cwd, None


def _legacy_exception(path: Path, name: str) -> bool:
    for parent in path.parents:
        config = parent / ".claude/file-protector.json"
        try:
            policy = json.loads(config.read_text(encoding="utf-8"))
        except FileNotFoundError:
            continue
        except (ValueError, OSError):
            return False
        patterns = (
            _patterns(policy, "excludePatterns", []) if isinstance(policy, dict) else []
        )
        return any(_safe_search(pattern, name) for pattern in patterns)
    return False


def _check_path(
    path: str,
    cwd: Path,
    config: Path,
    policy: dict,
    root: Path,
    project: dict | None,
    pi_runtime: bool,
) -> None:
    requested = Path(path).expanduser()
    raw_candidate = cwd / requested
    candidate = Path(os.path.abspath(raw_candidate))
    try:
        resolved = raw_candidate.resolve()
        config_target = config.resolve()
    except (OSError, ValueError, RuntimeError):
        _deny(path, "cannot resolve file or policy path", pi_runtime)
        return
    if resolved == config_target:
        _deny(path, "user hook policy", pi_runtime)
    names = (path, str(candidate), str(resolved))

    is_local = candidate.is_relative_to(root) and resolved.is_relative_to(root)
    relative = resolved.relative_to(root).as_posix() if is_local else None
    protected = _patterns(policy, "protectedPatterns", _DEFAULT_PROTECTED)
    if is_local:
        for pattern in _patterns(project or {}, "protectedPatterns", []):
            if _safe_search(pattern, relative or "") or _safe_search(
                pattern, candidate.relative_to(root).as_posix()
            ):
                _deny(path, f"project rule: {pattern}", pi_runtime)
    for pattern in protected:
        if not any(_safe_search(pattern, name) for name in names):
            continue
        if protected is _DEFAULT_PROTECTED and candidate == resolved:
            if relative in _patterns(project or {}, "allowPaths", []):
                break
            if (
                project is None
                and requested.is_absolute()
                and policy.get("allowLegacyProjectExcludes", True) is True
                and _legacy_exception(resolved, path)
            ):
                break
        source = "default rule" if protected is _DEFAULT_PROTECTED else "user rule"
        _deny(path, f"{source}: {pattern}", pi_runtime)

    warnings = _patterns(policy, "warnPatterns", _DEFAULT_WARN)
    for pattern in warnings:
        if any(_safe_search(pattern, name) for name in names):
            print(
                f"WARNING: Modifying sensitive file: {path} (matched {pattern})",
                file=sys.stderr,
            )
            break
    for pattern in _patterns(policy, "lockFilePatterns", _DEFAULT_LOCKS):
        if any(_safe_search(pattern, name) for name in names):
            print(f"WARNING: Modifying lock file: {path}", file=sys.stderr)
            print(
                "Lock files should typically be auto-generated by package managers",
                file=sys.stderr,
            )
            break


def main() -> None:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        sys.exit(0)

    if not isinstance(payload, dict):
        return

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
    event = payload["piEvent"] if pi_runtime else {}
    vendor = payload.get("vendorEvent")
    cwd_value = (
        event.get("cwd")
        or (vendor.get("cwd") if isinstance(vendor, dict) else None)
        or payload.get("cwd")
    )
    cwd = Path(cwd_value).resolve() if isinstance(cwd_value, str) else Path.cwd()
    config, policy, projects = _load_policy()
    root, project = _project_policy(projects, cwd)

    paths = [
        value
        for key in ("file_path", "path")
        if isinstance(value := tool_input.get(key), str) and value
    ]
    patch = tool_input.get("patch")
    if isinstance(patch, str):
        paths.extend(_extract_patch_paths(patch))
    for path in dict.fromkeys(paths):
        _check_path(path, cwd, config, policy, root, project, pi_runtime)

    if pi_runtime:
        print('{"decision":"allow"}')


if __name__ == "__main__":
    main()
