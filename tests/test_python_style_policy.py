from __future__ import annotations

import re
import tomllib

from conftest import REPO_ROOT


def test_ruff_target_version_does_not_enable_pep758_except_formatting() -> None:
    data = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())
    target = data["tool"]["ruff"].get("target-version")
    assert isinstance(target, str) and target.startswith("py")
    assert int(target.removeprefix("py")) < 314, (
        "Ruff py314+ formatting removes parentheses from multi-type except clauses; "
        "repo policy requires except (A, B):"
    )


def test_multi_type_except_clauses_stay_parenthesized() -> None:
    pattern = re.compile(
        r"^(?P<indent>\s*)except\s+(?!\()"
        r"[A-Za-z_][\w.]*\s*,\s*[A-Za-z_][\w.]*",
        re.MULTILINE,
    )
    roots = [REPO_ROOT / "scripts", REPO_ROOT / "src", REPO_ROOT / "tests"]
    offenders: list[str] = []
    for root in roots:
        for path in root.rglob("*.py"):
            rel = path.relative_to(REPO_ROOT)
            text = path.read_text()
            for match in pattern.finditer(text):
                line_no = text.count("\n", 0, match.start()) + 1
                offenders.append(f"{rel}:{line_no}: {match.group(0).strip()}")

    assert not offenders, "Use except (A, B):\n" + "\n".join(offenders)
