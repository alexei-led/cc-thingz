from __future__ import annotations

import re
from pathlib import Path

from conftest import REPO_ROOT

HOOK_ROOT = REPO_ROOT / "src" / "hooks"
BASH4_ONLY_PATTERNS = {
    r"\bmapfile\b": "mapfile is Bash 4+; macOS /bin/bash is 3.2",
    r"\breadarray\b": "readarray is Bash 4+; macOS /bin/bash is 3.2",
    r"\b(?:declare|local)\s+-A\b": (
        "associative arrays are Bash 4+; macOS /bin/bash is 3.2"
    ),
}


def test_shell_hooks_avoid_bash4_only_features() -> None:
    scripts: list[Path] = sorted(HOOK_ROOT.rglob("*.sh"))
    assert scripts

    for script in scripts:
        text = script.read_text()
        for pattern, reason in BASH4_ONLY_PATTERNS.items():
            assert not re.search(pattern, text), (
                f"{script.relative_to(REPO_ROOT)} uses {reason}"
            )
