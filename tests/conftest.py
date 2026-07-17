"""Shared pytest fixtures.

`load_script` loads a kebab-cased CLI script under scripts/ as an importable
module, mapping the filename to a snake-case module name.
"""

from __future__ import annotations

import importlib.util
import sys
import textwrap
from pathlib import Path
from types import ModuleType

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS = _REPO_ROOT / "scripts"

sys.path.insert(0, str(_SCRIPTS))


def _resolve(rel_or_name: str) -> Path:
    """Locate a script by relative path under scripts/, or by basename
    (searches scripts/validate/, scripts/evals/, scripts/release/).
    """
    direct = _SCRIPTS / rel_or_name
    if direct.is_file():
        return direct
    for sub in ("validate", "evals", "release"):
        candidate = _SCRIPTS / sub / rel_or_name
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(rel_or_name)


def _load(rel_or_name: str) -> ModuleType:
    path = _resolve(rel_or_name)
    module_name = path.stem.replace("-", "_")
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def load_script():
    """Return a function that loads a script in scripts/<sub>/ as a module."""
    return _load


REPO_ROOT: Path = _REPO_ROOT


def dedent_md(s: str) -> str:
    """Strip common leading whitespace and a leading blank line."""
    return textwrap.dedent(s).lstrip("\n")
