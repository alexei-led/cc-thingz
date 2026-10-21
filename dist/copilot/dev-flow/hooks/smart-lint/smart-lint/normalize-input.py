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
            next(group for group in match.groups() if group is not None)
            for match in PATCH_PATH.finditer(value)
        ]

    def clean(raw: object) -> str | None:
        if not isinstance(raw, str):
            return None
        value = raw.strip()
        if not value or "\x00" in value or "\n" in value or value == "/dev/null":
            return None
        return value

    def resolve(raw: str) -> Path | None:
        try:
            return (cwd / raw).resolve()
        except (OSError, ValueError, RuntimeError):
            return None

    if isinstance(tool_input, dict):
        for key in PATH_KEYS:
            value = clean(tool_input.get(key))
            if value is not None:
                candidates.append(value)
        for key in ("patch", "diff"):
            candidates.extend(
                value
                for raw in paths(tool_input.get(key))
                if (value := clean(raw)) is not None
            )

    outside = bool(candidates)
    for raw in candidates:
        full = resolve(raw)
        if full is None or full.is_relative_to(cwd):
            outside = False
            break

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

    def walk(value: object) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if key in PATH_KEYS:
                    add(child)
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)
        elif isinstance(value, str):
            for raw in paths(value):
                add(raw)

    walk(tool_input if isinstance(tool_input, dict) else data)
    return [str(int(pi)), str(cwd), session, str(int(outside)), *sorted(files)]


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except (ValueError, UnicodeError):
        data = {}
    sys.stdout.write("\0".join(normalize(data, Path.cwd())) + "\0")


if __name__ == "__main__":
    main()
