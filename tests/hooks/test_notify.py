from __future__ import annotations

import json
import os
import shlex
import stat
import subprocess
import textwrap
from pathlib import Path

from conftest import REPO_ROOT

HOOK = REPO_ROOT / "src" / "hooks" / "notify" / "hook.sh"


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content)
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def _run(
    payload: dict[str, str], cwd: Path, env: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        cwd=cwd,
        env=env,
        timeout=5,
        check=False,
    )


def _arg_after(args: list[str], flag: str) -> str:
    idx = args.index(flag)
    return args[idx + 1]


def test_idle_prompt_keeps_ready_message_and_targets_kitty_via_tmux(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / ".git").mkdir()

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    notifier_args = tmp_path / "terminal-notifier.args"

    _write_executable(
        bin_dir / "terminal-notifier",
        textwrap.dedent(
            f"""\
            #!/usr/bin/env bash
            printf '%s\n' "$@" > {shlex.quote(str(notifier_args))}
            """
        ),
    )
    _write_executable(
        bin_dir / "tmux",
        textwrap.dedent(
            """\
            #!/usr/bin/env bash
            case "$*" in
            *"#{client_termname}"*) echo "xterm-kitty" ;;
            *"#{client_tty}"*) echo "/dev/ttys001" ;;
            *"#{session_name}"*) echo "ccgram" ;;
            *"#{window_index}"*) echo "2" ;;
            *) exit 1 ;;
            esac
            """
        ),
    )
    _write_executable(
        bin_dir / "git",
        textwrap.dedent(
            """\
            #!/usr/bin/env bash
            if [[ "$1" == "-C" ]]; then
                shift 2
            fi
            if [[ "$1" == "branch" && "$2" == "--show-current" ]]; then
                echo "master"
                exit 0
            fi
            if [[ "$1" == "log" && "$2" == "--oneline" ]]; then
                echo "abc123 ruff running in pre-commit hooks"
                exit 0
            fi
            exit 1
            """
        ),
    )

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["TERM_PROGRAM"] = "tmux"
    env["TMUX"] = "/tmp/tmux-sock,1,0"
    env["TMUX_PANE"] = "%49"
    env.pop("KITTY_LISTEN_ON", None)
    env.pop("KITTY_PID", None)
    env.pop("KITTY_WINDOW_ID", None)
    env.pop("CLAUDE_TERMINAL_BUNDLE_ID", None)

    proc = _run(
        {
            "title": "Pi",
            "message": "Ready for input",
            "notification_type": "idle_prompt",
            "cwd": str(project),
            "session_id": "s1",
        },
        cwd=tmp_path,
        env=env,
    )

    assert proc.returncode == 0, proc.stderr
    args = notifier_args.read_text().splitlines()

    assert _arg_after(args, "-activate") == "net.kovidgoyal.kitty"
    assert _arg_after(args, "-message") == "Ready for input"
    assert "ruff running in pre-commit hooks" not in "\n".join(args)

    execute = _arg_after(args, "-execute")
    assert "open -b net.kovidgoyal.kitty" in execute
    assert "switch-client" in execute
    assert "/dev/ttys001" in execute
    assert "select-window" in execute
    assert "ccgram:2" in execute
    assert "select-pane" in execute
    assert "%49" in execute
