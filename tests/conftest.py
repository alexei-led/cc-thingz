"""Shared pytest fixtures.

`load_script` loads a kebab-cased CLI script under scripts/ as an importable
module, mapping the filename (e.g. `compile.py`) to a snake-case module name.
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
    (searches scripts/build/, scripts/validate/, scripts/evals/, scripts/release/).
    """
    direct = _SCRIPTS / rel_or_name
    if direct.is_file():
        return direct
    for sub in ("build", "validate", "evals", "release"):
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


# ---------------------------------------------------------------------------
# Shared constants — importable at collection time for @pytest.mark.parametrize
# ---------------------------------------------------------------------------

TARGETS: tuple[str, ...] = ("claude", "codex", "gemini", "pi")
REPO_ROOT: Path = _REPO_ROOT


def dedent_md(s: str) -> str:
    """Strip common leading whitespace and a leading blank line."""
    return textwrap.dedent(s).lstrip("\n")


# ---------------------------------------------------------------------------
# Staging-root helpers — plain functions, not fixtures (tmp_path is function-scoped)
# ---------------------------------------------------------------------------


def make_skill_staging_root(tmp_path: Path) -> Path:
    """Staging root for single-skill tests.

    Symlinks the entire `src/skills/` tree and the preambles directory so
    that `compile_skill` resolves paths relative to the returned root.
    """
    root = tmp_path / "repo"
    (root / "src").mkdir(parents=True)
    (root / "src" / "skills").symlink_to(_REPO_ROOT / "src" / "skills")
    (root / "scripts" / "build" / "preambles").mkdir(parents=True)
    for entry in (_REPO_ROOT / "scripts" / "build" / "preambles").iterdir():
        (root / "scripts" / "build" / "preambles" / entry.name).symlink_to(entry)
    return root


def make_batch_skill_staging_root(tmp_path: Path) -> Path:
    """Staging root for batch-skill tests.

    Creates per-skill symlinks under `src/skills/` so individual skills can be
    selectively absent without affecting sibling skills.
    """
    root = tmp_path / "repo"
    (root / "src" / "skills").mkdir(parents=True)
    for skill_dir in (_REPO_ROOT / "src" / "skills").iterdir():
        if skill_dir.is_dir():
            (root / "src" / "skills" / skill_dir.name).symlink_to(skill_dir)
    (root / "scripts" / "build" / "preambles").mkdir(parents=True)
    for entry in (_REPO_ROOT / "scripts" / "build" / "preambles").iterdir():
        (root / "scripts" / "build" / "preambles" / entry.name).symlink_to(entry)
    return root


def make_agent_staging_root(tmp_path: Path) -> Path:
    """Staging root for agent tests.

    Symlinks `src/agents/` only — agent compilation does not use preambles.
    """
    root = tmp_path / "repo"
    (root / "src").mkdir(parents=True)
    (root / "src" / "agents").symlink_to(_REPO_ROOT / "src" / "agents")
    return root
