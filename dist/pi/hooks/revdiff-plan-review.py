#!/usr/bin/env python3
"""Optional Pi wrapper for revdiff-planning's ExitPlanMode hook.

The actual planning hook lives in the revdiff package. This wrapper keeps
cc-thingz decoupled: if revdiff is not installed, plan execution proceeds.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import NoReturn

REVDIFF_PLANNING_PARTS = ("plugins", "revdiff-planning")
REVDIFF_PACKAGE_PARTS = ("github.com", "umputun", "revdiff", *REVDIFF_PLANNING_PARTS)


def agent_dir() -> Path:
    configured = os.environ.get("PI_CODING_AGENT_DIR")
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".pi" / "agent"


def candidate_roots() -> list[Path]:
    roots: list[Path] = []

    package_dir = os.environ.get("PI_PACKAGE_DIR")
    if package_dir:
        root = Path(package_dir).expanduser()
        roots.extend(
            [
                root / "git" / Path(*REVDIFF_PACKAGE_PARTS),
                root / Path(*REVDIFF_PACKAGE_PARTS),
            ]
        )

    cwd = Path.cwd()
    roots.append(cwd / ".pi" / "git" / Path(*REVDIFF_PACKAGE_PARTS))
    roots.append(agent_dir() / "git" / Path(*REVDIFF_PACKAGE_PARTS))
    return roots


def find_plugin_root() -> Path | None:
    for root in candidate_roots():
        hook = root / "scripts" / "plan-review-hook.py"
        if hook.is_file():
            return root
    return None


def allow() -> NoReturn:
    sys.exit(0)


def child_env(plugin_root: Path) -> dict[str, str]:
    env = {
        key: value for key, value in os.environ.items() if not key.startswith("PYTHON")
    }
    # Always guarantee a usable PATH: inherited PATH may be empty or broken under
    # some Pi launch contexts, in which case the child can't find `git`/`bash`.
    fallback_path = "/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin"
    if not env.get("PATH"):
        env["PATH"] = fallback_path
    env.setdefault("CLAUDE_PLUGIN_ROOT", str(plugin_root))
    env.setdefault("CLAUDE_PROJECT_DIR", str(Path.cwd()))
    env.setdefault("CLAUDE_PLUGIN_DATA", str(agent_dir() / "data" / "revdiff-planning"))
    return env


def python_executable() -> str | None:
    executable = Path(sys.executable)
    if executable.is_absolute() and executable.exists():
        return str(executable)
    return None


# Fallback timeout matches meta.yaml `pi.timeout` so a Pi build without the
# env var still gets a sane bound. Hook-runner exports PI_HOOK_TIMEOUT_SEC to
# avoid drift between this constant and the manifest-driven value.
_FALLBACK_TIMEOUT_SEC = 1740
# Margin so the inner subprocess exits with a proper blocking message before
# the parent (hook-runner) SIGKILLs it.
_PARENT_KILL_MARGIN_SEC = 5


def resolve_timeout() -> int:
    raw = os.environ.get("PI_HOOK_TIMEOUT_SEC")
    if not raw:
        return _FALLBACK_TIMEOUT_SEC
    try:
        parent_timeout = int(raw)
    except ValueError:
        return _FALLBACK_TIMEOUT_SEC
    if parent_timeout <= 0:
        return _FALLBACK_TIMEOUT_SEC
    return max(parent_timeout - _PARENT_KILL_MARGIN_SEC, 1)


def main() -> None:
    raw_stdin = sys.stdin.read()
    plugin_root = find_plugin_root()
    if plugin_root is None:
        allow()

    interpreter = python_executable()
    if interpreter is None:
        allow()

    hook = plugin_root / "scripts" / "plan-review-hook.py"
    try:
        result = subprocess.run(
            [interpreter, str(hook)],
            input=raw_stdin,
            capture_output=True,
            text=True,
            timeout=resolve_timeout(),
            env=child_env(plugin_root),
        )
    except subprocess.TimeoutExpired as exc:
        # Exit 2 = blocking. runPreToolUseGroups treats other non-zero codes as
        # non-blocking errors and continues, which would silently allow the plan.
        print(f"revdiff plan review timed out after {exc.timeout}s", file=sys.stderr)
        sys.exit(2)
    except (OSError, subprocess.SubprocessError) as exc:
        # Fail-open by design: this wrapper is opt-in (revdiff installed → review
        # the plan; not installed → proceed). A permission error or interpreter
        # failure on the upstream script falls into the same bucket as "plugin
        # not installed" rather than blocking plan execution. Operators who want
        # mandatory review should run the upstream hook directly, not via this
        # wrapper.
        print(f"revdiff plan review skipped: {exc}", file=sys.stderr)
        allow()

    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    sys.exit(result.returncode)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\r\033[K", end="")
        sys.exit(130)
