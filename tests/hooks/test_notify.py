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


def _path_without_jq() -> str:
    """Real PATH with every directory containing a jq binary removed."""
    parts = os.environ["PATH"].split(os.pathsep)
    kept = [p for p in parts if not (Path(p) / "jq").exists()]
    return os.pathsep.join(kept)


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content)
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def _write_terminal_notifier(bin_dir: Path, args_file: Path) -> None:
    _write_executable(
        bin_dir / "terminal-notifier",
        textwrap.dedent(
            f"""\
            #!/usr/bin/env bash
            printf '%s\n' "$@" > {shlex.quote(str(args_file))}
            """
        ),
    )


def _write_git(bin_dir: Path) -> None:
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


def _write_tmux(
    bin_dir: Path,
    *,
    term: str = "xterm-256color",
    tty: str = "/dev/ttys001",
    session: str = "main",
    window: str = "0",
    attached: str = "1",
    window_active: str = "0",
    pane_active: str = "0",
    term_program_global: str = "",
) -> None:
    """Mock tmux. term_program_global="" means TERM_PROGRAM unset in server env."""
    env_line = (
        f"TERM_PROGRAM={term_program_global}"
        if term_program_global
        else "-TERM_PROGRAM"
    )
    focus = f"{attached}:{window_active}:{pane_active}"
    _write_executable(
        bin_dir / "tmux",
        textwrap.dedent(
            f"""\
            #!/usr/bin/env bash
            case "$*" in
            *"show-environment"*) echo {shlex.quote(env_line)} ;;
            *"session_attached"*) echo {shlex.quote(focus)} ;;
            *"#{{client_termname}}"*) echo {shlex.quote(term)} ;;
            *"#{{client_tty}}"*) echo {shlex.quote(tty)} ;;
            *"#{{session_name}}"*) echo {shlex.quote(session)} ;;
            *"#{{window_index}}"*) echo {shlex.quote(window)} ;;
            *) exit 1 ;;
            esac
            """
        ),
    )


def _tmux_env(env: dict[str, str], bin_dir: Path) -> dict[str, str]:
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["TERM_PROGRAM"] = "tmux"
    env["TMUX"] = "/tmp/tmux-sock,1,0"
    env["TMUX_PANE"] = "%49"
    for var in (
        "KITTY_LISTEN_ON",
        "KITTY_PID",
        "KITTY_WINDOW_ID",
        "CLAUDE_TERMINAL_BUNDLE_ID",
    ):
        env.pop(var, None)
    return env


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

    _write_terminal_notifier(bin_dir, notifier_args)
    _write_git(bin_dir)
    # client is kitty, but the pane is not focused → notification must fire.
    _write_tmux(bin_dir, term="xterm-kitty", session="ccgram", window="2")

    env = _tmux_env(os.environ.copy(), bin_dir)

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


def test_idle_prompt_suppressed_when_pane_focused(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    notifier_args = tmp_path / "terminal-notifier.args"

    _write_terminal_notifier(bin_dir, notifier_args)
    # attached + active window + active pane → user is already looking at it.
    _write_tmux(bin_dir, term="xterm-kitty", window_active="1", pane_active="1")

    env = _tmux_env(os.environ.copy(), bin_dir)

    proc = _run(
        {
            "title": "Pi",
            "message": "Ready for input",
            "notification_type": "idle_prompt",
            "session_id": "s1",
        },
        cwd=tmp_path,
        env=env,
    )

    assert proc.returncode == 0, proc.stderr
    assert not notifier_args.exists(), "focused idle prompt should not notify"


def test_permission_prompt_not_suppressed_when_pane_focused(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    notifier_args = tmp_path / "terminal-notifier.args"

    _write_terminal_notifier(bin_dir, notifier_args)
    # focused pane — but permission prompts must always fire.
    _write_tmux(bin_dir, term="xterm-kitty", window_active="1", pane_active="1")

    env = _tmux_env(os.environ.copy(), bin_dir)

    proc = _run(
        {
            "title": "Pi",
            "message": "Allow shell command?",
            "notification_type": "permission_prompt",
            "session_id": "s1",
        },
        cwd=tmp_path,
        env=env,
    )

    assert proc.returncode == 0, proc.stderr
    args = notifier_args.read_text().splitlines()
    assert _arg_after(args, "-subtitle") == "Action required"
    assert _arg_after(args, "-activate") == "net.kovidgoyal.kitty"


def test_missing_jq_falls_back_without_crash(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    notifier_args = tmp_path / "terminal-notifier.args"
    _write_terminal_notifier(bin_dir, notifier_args)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{_path_without_jq()}"
    for var in (
        "TMUX",
        "TMUX_PANE",
        "TERM_PROGRAM",
        "KITTY_LISTEN_ON",
        "KITTY_PID",
        "KITTY_WINDOW_ID",
        "CLAUDE_TERMINAL_BUNDLE_ID",
    ):
        env.pop(var, None)

    proc = _run(
        {
            "title": "Pi",
            "message": "Ready for input",
            "notification_type": "idle_prompt",
        },
        cwd=tmp_path,
        env=env,
    )

    assert proc.returncode == 0, proc.stderr
    assert "command not found" not in proc.stderr
    assert "📢 Agent: Done" in proc.stderr
    assert not notifier_args.exists(), "should exit before invoking terminal-notifier"


def test_iterm_under_tmux_recovers_bundle_id(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    notifier_args = tmp_path / "terminal-notifier.args"

    _write_terminal_notifier(bin_dir, notifier_args)
    # Inside tmux TERM_PROGRAM is masked; the real terminal (iTerm) is only
    # recoverable from the server's startup environment.
    _write_tmux(
        bin_dir,
        term="xterm-256color",
        session="work",
        window="1",
        term_program_global="iTerm.app",
    )

    env = _tmux_env(os.environ.copy(), bin_dir)

    proc = _run(
        {
            "title": "Pi",
            "message": "Allow shell command?",
            "notification_type": "permission_prompt",
            "session_id": "s1",
        },
        cwd=tmp_path,
        env=env,
    )

    assert proc.returncode == 0, proc.stderr
    args = notifier_args.read_text().splitlines()
    assert _arg_after(args, "-activate") == "com.googlecode.iterm2"

    execute = _arg_after(args, "-execute")
    assert "open -b net.kovidgoyal.kitty" not in execute
    assert "switch-client" in execute
    assert "work:1" in execute


def test_kitty_via_socket_without_tmux(tmp_path: Path) -> None:
    import shutil
    import socket as _socket
    import tempfile

    # AF_UNIX paths are capped at ~104 chars, so bind under a short /tmp dir
    # rather than the (long) pytest tmp_path.
    sock_dir = tempfile.mkdtemp(prefix="ccn-", dir="/tmp")
    sock_path = Path(sock_dir) / "k.sock"
    srv = _socket.socket(_socket.AF_UNIX)
    srv.bind(str(sock_path))

    try:
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        notifier_args = tmp_path / "terminal-notifier.args"

        _write_terminal_notifier(bin_dir, notifier_args)
        _write_executable(bin_dir / "kitty", "#!/usr/bin/env bash\nexit 0\n")

        env = os.environ.copy()
        env["PATH"] = f"{bin_dir}:{env['PATH']}"
        env["KITTY_LISTEN_ON"] = f"unix:{sock_path}"
        env["KITTY_WINDOW_ID"] = "7"
        for var in ("TMUX", "TMUX_PANE", "TERM_PROGRAM", "CLAUDE_TERMINAL_BUNDLE_ID"):
            env.pop(var, None)

        proc = _run(
            {
                "title": "Pi",
                "message": "Allow shell command?",
                "notification_type": "permission_prompt",
                "session_id": "s1",
            },
            cwd=tmp_path,
            env=env,
        )

        assert proc.returncode == 0, proc.stderr
        args = notifier_args.read_text().splitlines()
        assert _arg_after(args, "-activate") == "net.kovidgoyal.kitty"

        execute = _arg_after(args, "-execute")
        assert "open -b net.kovidgoyal.kitty" in execute
        assert "focus-tab -m window_id:'7'" in execute
        assert "switch-client" not in execute
    finally:
        srv.close()
        shutil.rmtree(sock_dir, ignore_errors=True)
