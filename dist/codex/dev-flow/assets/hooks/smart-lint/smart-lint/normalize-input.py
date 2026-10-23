"""Normalize one hook payload into NUL-delimited fields for the Bash runner."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PATCH_PATH = re.compile(
    r"^\*\*\* (?:(?:Update|Add|Delete) File|Move to): (.+)$"
    r"|^\+\+\+ b/(.+)$|^--- a/(.+)$|^diff --git a/(.+?) b/.+$",
    re.MULTILINE,
)
PATH_KEYS = {
    "file_path",
    "path",
    "filename",
    "notebook_path",
    "source_file",
    "target_file",
}


def normalize(data: object, default_cwd: Path) -> list[str]:
    if not isinstance(data, dict):
        data = {}
    pi = data.get("event") == "post-tool" and isinstance(data.get("piEvent"), dict)
    source = data["piEvent"] if pi else data
    vendor = data.get("vendorEvent")
    vendor = vendor if pi and isinstance(vendor, dict) else {}
    raw_cwd = source.get("cwd")
    if not isinstance(raw_cwd, str):
        raw_cwd = vendor.get("cwd")
    cwd = default_cwd.resolve()
    if isinstance(raw_cwd, str) and "\x00" not in raw_cwd:
        candidate = Path(raw_cwd)
        if candidate.is_dir():
            cwd = candidate.resolve()
    session = str(
        source.get("session_id")
        or vendor.get("session_id")
        or data.get("session_id")
        or "default"
    )
    session = session.replace("\x00", "_")
    tool_input = source.get("input") if pi else data.get("tool_input")
    candidates: list[str] = []
    files: set[str] = set()

    def paths(value: object) -> list[str]:
        if not isinstance(value, str):
            return []
        return [
            next(group for group in match.groups() if group is not None).removesuffix(
                "\r"
            )
            for match in PATCH_PATH.finditer(value)
        ]

    def clean(raw: object) -> str | None:
        if not isinstance(raw, str):
            return None
        value = raw
        if not value or "\x00" in value or "\n" in value or value == "/dev/null":
            return None
        return value

    def resolve(raw: str) -> Path | None:
        try:
            return (cwd / raw).resolve()
        except (OSError, ValueError, RuntimeError):
            return None

    def add(raw: object) -> None:
        value = clean(raw)
        if value is None:
            return
        path = Path(value)
        if not path.is_absolute() and ".." in path.parts:
            return
        full = resolve(value)
        if full is not None and full.is_relative_to(cwd) and full.is_file():
            files.add(full.relative_to(cwd).as_posix())

    payload = tool_input if isinstance(tool_input, (dict, list, str)) else data

    def explicit_paths(value: object) -> list[str]:
        result: list[str] = []
        if isinstance(value, dict):
            for key, child in value.items():
                if key in PATH_KEYS and (path := clean(child)) is not None:
                    result.append(path)
                if isinstance(child, (dict, list)):
                    result.extend(explicit_paths(child))
        elif isinstance(value, list):
            for child in value:
                result.extend(explicit_paths(child))
        return result

    candidates = explicit_paths(payload)
    if candidates:
        for candidate in candidates:
            add(candidate)
    else:

        def patches(value: object, raw_patch: bool = False) -> None:
            if isinstance(value, dict):
                for key, child in value.items():
                    patches(
                        child,
                        key in {"patch", "patches", "diff", "input", "tool_input"},
                    )
            elif isinstance(value, list):
                for child in value:
                    patches(child, raw_patch)
            elif isinstance(value, str) and raw_patch:
                for raw in paths(value):
                    if (candidate := clean(raw)) is not None:
                        candidates.append(candidate)
                        add(candidate)

        patches(payload, isinstance(payload, (str, list)))

    outside = bool(candidates) and all(
        (full := resolve(raw)) is not None and not full.is_relative_to(cwd)
        for raw in candidates
    )
    targeted = bool(candidates) or tool_input is not None or pi
    unavailable = targeted and not files and not outside
    status = "1" if outside else "2" if unavailable else "0"
    return [str(int(pi)), str(cwd), session, status, *sorted(files)]


def main() -> int:
    try:
        raw = sys.stdin.read()
        data = json.loads(raw if raw.strip() else "{}")
        if not isinstance(data, dict):
            raise ValueError("hook input must be an object")
        pi = data.get("event") == "post-tool" and "piEvent" in data
        if pi and not isinstance(data["piEvent"], dict):
            raise ValueError("invalid Pi event")
        source = data["piEvent"] if pi else data
        vendor = data.get("vendorEvent")
        vendor = vendor if pi and isinstance(vendor, dict) else {}
        cwd = source.get("cwd")
        if cwd is None:
            cwd = vendor.get("cwd")
        if cwd is not None and (
            not isinstance(cwd, str)
            or "\x00" in cwd
            or (cwd and not Path(cwd).is_dir())
        ):
            raise ValueError("invalid project cwd")
    except (ValueError, UnicodeError):
        print("smart-lint: invalid hook input; checks skipped", file=sys.stderr)
        return 1
    sys.stdout.write("\0".join(normalize(data, Path.cwd())) + "\0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
