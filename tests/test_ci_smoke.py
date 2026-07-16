"""CI smoke tests for the direct Agent Bundler build."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

from conftest import REPO_ROOT as _REPO_ROOT


def _hash_tree(root: Path) -> dict[str, str]:
    digests: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        digests[str(path.relative_to(root))] = hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
    return digests


def test_hash_tree_ignores_pycache_noise(tmp_path: Path) -> None:
    (tmp_path / "SKILL.md").write_text("hello\n", encoding="utf-8")
    before = _hash_tree(tmp_path)
    cache_dir = tmp_path / "scripts" / "__pycache__"
    cache_dir.mkdir(parents=True)
    (cache_dir / "helper.cpython-314.pyc").write_bytes(b"bytecode")
    (tmp_path / "stray.pyc").write_bytes(b"bytecode")
    assert before == _hash_tree(tmp_path)


def test_agbun_build_is_idempotent() -> None:
    dist = _REPO_ROOT / "dist"
    subprocess.run(["agbun", "build", "--root", str(_REPO_ROOT)], check=True)
    before = _hash_tree(dist)
    subprocess.run(["agbun", "build", "--root", str(_REPO_ROOT)], check=True)
    assert before == _hash_tree(dist)
    subprocess.run(["agbun", "check", "--root", str(_REPO_ROOT)], check=True)
