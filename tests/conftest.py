"""Shared pytest fixtures.

`load_script` loads a kebab-cased CLI script under scripts/ as an importable
module, mapping the filename to a snake-case module name.
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
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


@pytest.fixture(scope="session")
def cleanup_repo_template(tmp_path_factory: pytest.TempPathFactory) -> Path:
    from git_helpers import create_cleanup_clone

    return create_cleanup_clone(tmp_path_factory.mktemp("cleanup-template"))


@pytest.fixture
def clone(cleanup_repo_template: Path, tmp_path: Path) -> Path:
    """Copy an immutable seed; refs, worktrees, and config stay test-local."""
    return Path(shutil.copytree(cleanup_repo_template, tmp_path / "work"))


REPO_ROOT: Path = _REPO_ROOT


def dedent_md(s: str) -> str:
    """Strip common leading whitespace and a leading blank line."""
    return textwrap.dedent(s).lstrip("\n")


def pytest_sessionstart(session: pytest.Session) -> None:
    # Temporary repositories must not invoke the developer's signer or hooks.
    isolation = pytest.MonkeyPatch()
    isolation.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    isolation.setenv("GIT_CONFIG_NOSYSTEM", "1")
    session.config.add_cleanup(isolation.undo)
    required = os.environ.get("CC_THINGZ_REQUIRED_CLIS", "").split(",")
    missing = [name for name in required if name and shutil.which(name) is None]
    if missing:
        raise pytest.UsageError(f"Required runtime CLIs missing: {', '.join(missing)}")
    # `agbun package` needs the untracked build metadata (.agentbundler/build.json),
    # and several tests read dist/ directly, so it must match current src/.
    # Build once, in the controller, before workers start, and let tests just
    # read dist/.
    is_worker = hasattr(session.config, "workerinput")
    if not is_worker and shutil.which("agbun"):
        subprocess.run(["agbun", "build", "--root", str(_REPO_ROOT)], check=True)
