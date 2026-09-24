#!/usr/bin/env python3
"""Optionally block malformed direct GitHub release create/edit commands."""

from __future__ import annotations

import json
import os
import re
import shlex
import sys
from pathlib import Path
from typing import NoReturn

sys.dont_write_bytecode = True


def _notes_scripts_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "skills" / "releasing-code" / "scripts"
        if (candidate / "release_notes.py").is_file():
            return candidate
    raise RuntimeError("packaged releasing-code notes checker was not found")


sys.path.insert(0, str(_notes_scripts_dir()))

from release_notes import (  # noqa: E402
    ReleaseNotesError,
    validate_notes,
    validate_repository,
    version_from_tag,
)

SEPARATORS = {";", "&&", "||", "|", "&", ">", "<", "\n"}
VALUE_OPTIONS = {"--title", "--notes-file", "--repo"}
READ_ONLY_COMMANDS = {"list", "view", "download"}
MUTATING_COMMANDS = {"create", "edit", "upload", "delete"}


class GuardError(ValueError):
    """Raised when a supported release command is malformed or unsupported."""


def _deny(message: str, pi_runtime: bool) -> NoReturn:
    if pi_runtime:
        print(json.dumps({"decision": "deny", "reason": message}))
        raise SystemExit(0)
    print(f"BLOCKED: {message}", file=sys.stderr)
    raise SystemExit(2)


def _tokens(command: str) -> list[str]:
    lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|<>\n")
    lexer.whitespace = " \t\r"
    lexer.whitespace_split = True
    lexer.commenters = ""
    return list(lexer)


def _is_release_command(tokens: list[str]) -> bool:
    return len(tokens) >= 2 and Path(tokens[0]).name == "gh" and tokens[1] == "release"


def _find_wrapped_release_mutation(tokens: list[str]) -> bool:
    if tokens and Path(tokens[0]).name in {"echo", "printf"}:
        return False
    for index, token in enumerate(tokens[:-2]):
        if (
            Path(token).name == "gh"
            and tokens[index + 1] == "release"
            and tokens[index + 2] in MUTATING_COMMANDS
        ):
            return True
    return False


def _split_segments(tokens: list[str]) -> list[list[str]]:
    segments: list[list[str]] = [[]]
    for token in tokens:
        if token in SEPARATORS:
            segments.append([])
        else:
            segments[-1].append(token)
    return [segment for segment in segments if segment]


def _parse_supported_options(
    arguments: list[str],
) -> tuple[list[str], dict[str, str], set[str]]:
    positionals: list[str] = []
    options: dict[str, str] = {}
    flags: set[str] = set()
    index = 0
    while index < len(arguments):
        token = arguments[index]
        if token == "--dry-run":
            flags.add(token)
            index += 1
            continue
        if token == "--verify-tag":
            flags.add(token)
            index += 1
            continue
        if token in VALUE_OPTIONS:
            if index + 1 >= len(arguments):
                raise GuardError(f"{token} requires a value")
            if token in options:
                raise GuardError(f"duplicate option: {token}")
            options[token] = arguments[index + 1]
            index += 2
            continue
        if token.startswith("--"):
            name, separator, value = token.partition("=")
            if name not in VALUE_OPTIONS or not separator or name in options:
                raise GuardError(f"unsupported release option: {token}")
            options[name] = value
            index += 1
            continue
        if token.startswith("-"):
            raise GuardError(f"unsupported release option: {token}")
        positionals.append(token)
        index += 1
    return positionals, options, flags


def _validate_publish(tokens: list[str]) -> None:
    if len(tokens) < 3 or tokens[2] in {"--help", "help"}:
        return
    operation = tokens[2]
    if operation in READ_ONLY_COMMANDS:
        return
    if operation not in {"create", "edit"}:
        raise GuardError(f"unsupported GitHub release command: {operation}")

    arguments = tokens[3:]
    if arguments == ["--help"] or "--dry-run" in arguments:
        return
    positionals, options, flags = _parse_supported_options(arguments)
    if len(positionals) != 1:
        raise GuardError("release create/edit requires exactly one tag argument")
    tag = positionals[0]
    version_from_tag(tag)
    if options.get("--title") != tag:
        raise GuardError("release title must exactly match its tag")
    repository = options.get("--repo")
    if repository is None:
        raise GuardError("release create/edit requires an explicit --repo owner/name")
    validate_repository(repository)
    notes_file = options.get("--notes-file")
    if not notes_file or notes_file == "-":
        raise GuardError(
            "release create/edit requires --notes-file with the reviewed notes"
        )
    if operation == "create" and "--verify-tag" not in flags:
        raise GuardError("release create requires --verify-tag")

    path = Path(notes_file).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    try:
        validate_notes(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise GuardError(f"cannot read release notes {path}: {exc}") from exc
    except ReleaseNotesError as exc:
        raise GuardError(str(exc)) from exc


def check_command(command: str) -> str | None:
    try:
        tokens = _tokens(command)
    except ValueError as exc:
        if re.search(r"\bgh\s+release\s+(create|edit|upload|delete)\b", command):
            raise GuardError("unbalanced quoting in a GitHub release command") from exc
        return None
    segments = _split_segments(tokens)
    release_segments = [segment for segment in segments if _is_release_command(segment)]
    if len(segments) > 1 and release_segments:
        raise GuardError(
            "compound shell commands containing GitHub releases are unsupported; "
            "run one direct release command at a time"
        )
    if release_segments:
        _validate_publish(release_segments[0])
    elif _find_wrapped_release_mutation(tokens):
        raise GuardError(
            "wrapped GitHub release commands are unsupported; run one direct gh command"
        )
    return None


def _command_from_payload(payload: object) -> tuple[str, bool]:
    if not isinstance(payload, dict):
        return "", False
    pi_event = payload.get("piEvent")
    pi_runtime = payload.get("event") == "pre-tool" and isinstance(pi_event, dict)
    tool_input = (
        pi_event.get("input", {}) if pi_runtime else payload.get("tool_input", {})
    )
    if not isinstance(tool_input, dict):
        return "", pi_runtime
    command = tool_input.get("command", "")
    return (command if isinstance(command, str) else ""), pi_runtime


def main() -> None:
    if os.environ.get("HOOK_RELEASE_GUARD") != "1":
        return
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        return
    command, pi_runtime = _command_from_payload(payload)
    if not command:
        return
    try:
        check_command(command)
    except GuardError as exc:
        _deny(f"release-guard: {exc}", pi_runtime)
    if pi_runtime:
        print('{"decision":"allow"}')


if __name__ == "__main__":
    main()
