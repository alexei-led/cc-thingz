"""Checkout entry point for the shipped installation doctor."""

import runpy
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_DOCTOR = _REPO / "src/skills/installation-doctor/scripts/doctor.py"
_API = runpy.run_path(str(_DOCTOR))
inspect = _API["inspect"]
Inspection = _API["Inspection"]


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    return _API["main"](["--repo", str(_REPO), *arguments])


if __name__ == "__main__":
    raise SystemExit(main())
