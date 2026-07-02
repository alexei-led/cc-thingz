"""CI smoke test: a fresh compile produces the same dist/ as the committed one.

This is the local stand-in for the CI drift check (`make check`): we invoke the
compiler in-process and confirm the build is deterministic — running it twice
yields identical file content. That's the same property `git diff --exit-code`
proves on CI, but it works inside pytest without depending on a clean tree.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from conftest import REPO_ROOT as _REPO_ROOT


def _hash_tree(root: Path) -> dict[str, str]:
    digests: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            # Gitignored bytecode cache, not a build artifact. Other tests in
            # the same pytest session import dist/ scripts and populate these
            # as a side effect, which flaked this idempotency check.
            continue
        rel = str(path.relative_to(root))
        digests[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return digests


def test_hash_tree_ignores_pycache_noise(tmp_path: Path) -> None:
    """Regression: a stray __pycache__/*.pyc appearing between two snapshots
    (a side effect of an unrelated test importing a dist/ script in the same
    pytest session) must not register as build drift. Real build artifacts
    must still be hashed.
    """
    (tmp_path / "SKILL.md").write_text("hello\n", encoding="utf-8")
    before = _hash_tree(tmp_path)

    cache_dir = tmp_path / "scripts" / "__pycache__"
    cache_dir.mkdir(parents=True)
    (cache_dir / "helper.cpython-314.pyc").write_bytes(b"bytecode")
    (tmp_path / "stray.pyc").write_bytes(b"bytecode")

    after = _hash_tree(tmp_path)

    assert before == after
    assert after == {"SKILL.md": hashlib.sha256(b"hello\n").hexdigest()}


@pytest.fixture(scope="module")
def compile_mod(load_script):
    return load_script("build/compile.py")


def test_main_dry_run_succeeds(compile_mod):
    assert compile_mod.main(["--dry-run"]) == 0


def test_build_is_idempotent(compile_mod):
    dist = _REPO_ROOT / "dist"
    if not dist.is_dir():
        pytest.skip("dist/ not present; run `make build` first")

    before = _hash_tree(dist)
    assert compile_mod.main([]) == 0
    after = _hash_tree(dist)

    changed = sorted(p for p, h in after.items() if before.get(p) != h)
    added = sorted(p for p in after if p not in before)
    removed = sorted(p for p in before if p not in after)

    assert not changed, f"rebuild mutated existing files: {changed[:5]}"
    assert not added, f"rebuild produced new files: {added[:5]}"
    assert not removed, f"rebuild removed files: {removed[:5]}"
