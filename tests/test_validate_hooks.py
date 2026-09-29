"""Generated hook configs reference real files and run from the installed layout."""

from __future__ import annotations

import json
import os
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from conftest import REPO_ROOT

DIST = REPO_ROOT / "dist"
OK_CODEX_COMMAND = 'bash "${PLUGIN_ROOT}/assets/hooks/ok/hook.sh"'
# Desktop notifications are real side effects; the static check covers them.
SKIPPED_RUNTIME_EVENTS = {"Notification"}
MISSING_FILE_MARKERS = ("No such file", "can't open file", "not found")


@pytest.fixture(scope="module")
def vh(load_script):
    return load_script("validate_hooks.py")


def _write_json(path: Path, value: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value if isinstance(value, str) else json.dumps(value))
    return path


def _touch(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/usr/bin/env bash\nexit 0\n")


def _codex_config(command: str, *, event: str = "Stop", **extra) -> dict:
    return {
        "hooks": {
            event: [
                {
                    **extra,
                    "hooks": [{"type": "command", "command": command, "timeout": 5}],
                }
            ]
        }
    }


def _valid_pi(pi: Path) -> None:
    _touch(pi / "hooks/payloads/guard/hook.sh")
    _touch(pi / "hooks/notify.sh")
    _write_json(
        pi / "hooks/hooks.v1.json",
        {
            "version": 1,
            "hooks": [
                {
                    "identity": "hook/guard",
                    "event": "pre-tool",
                    "handler": {
                        "mode": "exec",
                        "program": "bash",
                        "arguments": [{"packageFile": "hooks/payloads/guard/hook.sh"}],
                    },
                    "timeoutMilliseconds": 1000,
                }
            ],
        },
    )
    _write_json(
        pi / "extensions/hooks.json",
        {
            "hooks": {
                "Stop": [{"hooks": [{"type": "command", "command": "ccgram hook"}]}],
                "Notification": [
                    {
                        "hooks": [
                            {
                                "type": "command",
                                "command": "bash ${PI_HOOKS_DIR}/notify.sh",
                            }
                        ]
                    }
                ],
            }
        },
    )


def test_repository_dist_hooks_reference_existing_files(vh) -> None:
    assert vh.validate_dist(DIST) == []


def test_cli_reports_errors_with_nonzero_exit(vh, tmp_path: Path, capsys) -> None:
    _write_json(
        tmp_path / "codex/dev-flow/hooks/hooks.json",
        _codex_config("'bash' \"${PLUGIN_ROOT}\"'/assets/hooks/gone/hook.sh'"),
    )

    assert vh.main(["--dist", str(tmp_path)]) == 1
    assert "missing referenced file" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("target", "relative", "config", "expected"),
    [
        (
            "codex",
            "dev-flow/hooks/hooks.json",
            _codex_config("'python3' \"${PLUGIN_ROOT}\"'/assets/hooks/gone/hook.py'"),
            "missing referenced file",
        ),
        (
            "codex",
            "dev-flow/hooks/hooks.json",
            _codex_config('bash "${CLAUDE_PLUGIN_ROOT}/assets/hooks/ok/hook.sh"'),
            "uses ${CLAUDE_PLUGIN_ROOT}",
        ),
        (
            "codex",
            "dev-flow/hooks/hooks.json",
            _codex_config(
                'bash "${PLUGIN_ROOT}/assets/hooks/ok/hook.sh"', event="Stopp"
            ),
            "unknown codex hook event",
        ),
        (
            "codex",
            "dev-flow/hooks/hooks.json",
            _codex_config(
                'bash "${PLUGIN_ROOT}/assets/hooks/ok/hook.sh"', matcher="(Bash"
            ),
            "invalid matcher",
        ),
        (
            "codex",
            "dev-flow/hooks/hooks.json",
            _codex_config("echo hello"),
            "does not run a packaged file",
        ),
        (
            "codex",
            "dev-flow/hooks/hooks.json",
            _codex_config('bash "${PLUGIN_ROOT}/../../../etc/hosts"'),
            "escapes the plugin root",
        ),
        (
            "codex",
            "dev-flow/hooks/hooks.json",
            {
                "hooks": {
                    "Stop": [
                        {
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": OK_CODEX_COMMAND,
                                    "timeout": 0,
                                }
                            ]
                        }
                    ]
                }
            },
            "timeout must be a positive number",
        ),
        (
            "codex",
            "dev-flow/hooks/hooks.json",
            {"hooks": {"Stop": [{"hooks": []}]}},
            "expected a non-empty 'hooks' list",
        ),
        ("codex", "dev-flow/hooks/hooks.json", "{not json", "unreadable JSON"),
        ("codex", "dev-flow/hooks/hooks.json", {"Stop": []}, "'hooks' object"),
        (
            "claude",
            "dev-flow/hooks/hooks.json",
            {
                "hooks": {
                    "Stop": [
                        {
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": "bash",
                                    "args": [
                                        "${CLAUDE_PLUGIN_ROOT}/hooks/gone/hook.sh"
                                    ],
                                }
                            ]
                        }
                    ]
                }
            },
            "missing referenced file",
        ),
        (
            "copilot",
            "dev-flow/hooks.json",
            {
                "version": 1,
                "hooks": {
                    "PreToolUse": [
                        {
                            "type": "command",
                            "bash": 'bash "${PLUGIN_ROOT}/hooks/gone.sh"',
                        }
                    ]
                },
            },
            "missing referenced file",
        ),
        (
            "cursor",
            "dev-flow/hooks/hooks.json",
            {
                "version": 1,
                "hooks": {"stop": [{"command": "bash ./hooks/gone/hook.sh"}]},
            },
            "missing referenced file",
        ),
        (
            "cursor",
            "dev-flow/hooks/hooks.json",
            {
                "version": 1,
                "hooks": {
                    "stop": [{"command": 'bash "${PLUGIN_ROOT}/hooks/ok/hook.sh"'}]
                },
            },
            "uses ${PLUGIN_ROOT}",
        ),
        (
            "cursor",
            "dev-flow/hooks/hooks.json",
            {"version": 1, "hooks": {"Stop": [{"command": "bash ./hooks/ok/hook.sh"}]}},
            "unknown cursor hook event",
        ),
        (
            "grok",
            "dev-flow/hooks/hooks.json",
            {
                "hooks": {
                    "Stop": [
                        {
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": "bash",
                                    "args": ["${GROK_PLUGIN_ROOT}/hooks/gone/hook.sh"],
                                }
                            ]
                        }
                    ]
                }
            },
            "missing referenced file",
        ),
    ],
)
def test_vendor_config_defects_are_reported(
    vh, tmp_path: Path, target: str, relative: str, config: object, expected: str
) -> None:
    plugin = tmp_path / target / "dev-flow"
    _touch(plugin / "assets/hooks/ok/hook.sh")
    _touch(plugin / "hooks/ok/hook.sh")
    _write_json(tmp_path / target / relative, config)

    errors = vh.validate_dist(tmp_path)

    assert any(expected in error for error in errors), errors


def test_valid_fixture_passes(vh, tmp_path: Path) -> None:
    _touch(tmp_path / "codex/dev-flow/assets/hooks/ok/hook.sh")
    _write_json(
        tmp_path / "codex/dev-flow/hooks/hooks.json",
        _codex_config("'bash' \"${PLUGIN_ROOT}\"'/assets/hooks/ok/hook.sh'"),
    )
    _valid_pi(tmp_path / "pi")

    assert vh.validate_dist(tmp_path) == []


def test_empty_dist_is_an_error(vh, tmp_path: Path) -> None:
    assert vh.validate_dist(tmp_path) == [
        f"{tmp_path}: no generated hook configs found"
    ]


@pytest.mark.parametrize(
    ("mutate", "expected"),
    [
        (
            lambda pi: (pi / "hooks/payloads/guard/hook.sh").unlink(),
            "missing referenced file",
        ),
        (lambda pi: (pi / "hooks/notify.sh").unlink(), "missing referenced file"),
        (
            lambda pi: _write_json(pi / "hooks/hooks.v1.json", {"hooks": {}}),
            "invalid portable manifest",
        ),
        (
            lambda pi: _write_json(
                pi / "hooks/hooks.v1.json",
                {
                    "hooks": [
                        {
                            "identity": "hook/x",
                            "event": "before-everything",
                            "handler": {"program": "ruby", "arguments": []},
                            "timeoutMilliseconds": 1,
                        }
                    ]
                },
            ),
            "handler program must be one of",
        ),
    ],
)
def test_pi_defects_are_reported(vh, tmp_path: Path, mutate, expected: str) -> None:
    pi = tmp_path / "pi"
    _valid_pi(pi)
    mutate(pi)

    errors = vh.validate_pi(pi)

    assert any(expected in error for error in errors), errors


# --- Runtime smoke: execute every generated command as the vendor would ---


def _registrations(vh) -> list[tuple[str, Path, str, str | None, dict]]:
    found = []
    for target, plugin_root, config in vh.iter_hook_configs(DIST):
        spec = vh.TARGETS[target]
        data = json.loads(config.read_text())
        for event, groups in data["hooks"].items():
            for handler, matcher in vh._handlers(spec, groups, event, []):
                found.append((target, plugin_root, event, matcher, handler))
    return found


def _invoke(
    vh,
    target: str,
    plugin_root: Path,
    event: str,
    matcher: str | None,
    handler: dict,
    work: Path,
) -> subprocess.CompletedProcess[str]:
    spec = vh.TARGETS[target]
    shell_tool = (
        matcher is not None and re.search(matcher, "Bash") or matcher == "Shell"
    )
    tool_input = (
        {"command": "true"}
        if shell_tool
        else {"file_path": str(work / "notes.txt"), "content": "hello\n"}
    )
    payload = {
        "hook_event_name": event,
        "session_id": "hook-smoke",
        "cwd": str(work),
        "tool_name": "Bash" if shell_tool else "Write",
        "tool_input": tool_input,
        "prompt": "hello",
    }
    root_variable = spec.root_variable or "PLUGIN_ROOT"
    environment = {
        "PATH": os.environ["PATH"],
        "HOME": str(work),
        "SKIP_LINT": "1",
        "SKIP_TESTS": "1",
        root_variable: str(plugin_root),
    }
    command = handler[spec.command_key]
    if handler.get("args"):
        argv = [
            command,
            *(
                arg.replace(f"${{{root_variable}}}", str(plugin_root))
                for arg in handler["args"]
            ),
        ]
    else:
        argv = ["bash", "-c", command]
    return subprocess.run(
        argv,
        cwd=plugin_root if spec.root_variable is None else work,
        env=environment,
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=60,
    )


def _git_work(path: Path) -> Path:
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    return path


@pytest.fixture()
def git_work(tmp_path: Path) -> Path:
    return _git_work(tmp_path / "work")


def test_every_generated_command_runs_from_its_plugin_root(vh, tmp_path: Path) -> None:
    registrations = [
        registration
        for registration in _registrations(vh)
        if registration[2] not in SKIPPED_RUNTIME_EVENTS
    ]

    def run(index: int) -> str | None:
        target, plugin_root, event, matcher, handler = registrations[index]
        work = _git_work(tmp_path / f"work-{index}")
        result = _invoke(vh, target, plugin_root, event, matcher, handler, work)
        output = result.stdout + result.stderr
        if (
            result.returncode == 0
            and not any(marker in output for marker in MISSING_FILE_MARKERS)
            and '"deny"' not in result.stdout
        ):
            return None
        name = f"{target}/{plugin_root.name} {event}"
        return f"{name}: exit {result.returncode}: {output[-300:]}"

    with ThreadPoolExecutor(max_workers=8) as pool:
        outcomes = pool.map(run, range(len(registrations)))
        failures = [failure for failure in outcomes if failure]

    assert failures == []


def test_stale_plugin_root_is_detected(vh, git_work: Path, tmp_path: Path) -> None:
    """Codex replaces versioned plugin dirs under live sessions, deleting old roots."""
    stale = tmp_path / "plugins/cache/cc-thingz/dev-flow/0.0.0"
    registrations = [
        registration
        for registration in _registrations(vh)
        if registration[0] == "codex" and registration[1].name == "dev-flow"
    ]
    assert registrations

    results = {
        (event, matcher): _invoke(vh, "codex", stale, event, matcher, handler, git_work)
        for _, _, event, matcher, handler in registrations
    }

    assert results[("Stop", None)].returncode == 127
    assert all(
        result.returncode != 0 or '"deny"' in result.stdout
        for result in results.values()
    )
    assert vh.validate_config(
        "codex", stale, REPO_ROOT / "dist/codex/dev-flow/hooks/hooks.json"
    )
