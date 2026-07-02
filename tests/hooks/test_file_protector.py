"""Tests for src/hooks/file-protector/hook.py.

Two input shapes:
  - Single-file: {"tool_input": {"file_path": "..."}}  (Claude Code Write/Edit)
  - Patch:       {"tool_input": {"patch": "..."}}       (Codex apply_patch, multi-file)

All tests use a temp HOME to isolate from the user's real hook-config.json,
which forces the hook to use its built-in default patterns.
Config-override tests write a synthetic hook-config.json into that temp HOME.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

HOOK = (
    Path(__file__).resolve().parent.parent.parent
    / "src"
    / "hooks"
    / "file-protector"
    / "hook.py"
)


@pytest.fixture
def home(tmp_path: Path) -> Path:
    """Temp HOME with no hook-config.json — hook falls back to built-in defaults."""
    (tmp_path / ".claude").mkdir()
    return tmp_path


def _run(payload: dict, home: Path | None = None) -> tuple[int, str]:
    env = os.environ.copy()
    if home:
        env["HOME"] = str(home)
    result = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
    )
    return result.returncode, result.stderr


def _single(path: str, home: Path | None = None) -> tuple[int, str]:
    return _run({"tool_input": {"file_path": path}}, home)


def _patch(patch: str, home: Path | None = None) -> tuple[int, str]:
    return _run({"tool_input": {"patch": patch}}, home)


# ---------------------------------------------------------------------------
# Safe paths — must exit 0, no output
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    [
        "src/main.py",
        "README.md",
        "tests/test_foo.py",
        "docs/api.md",
        ".gitignore",
        "Makefile",
        "config/settings.yaml",
        "scripts/deploy.sh",
    ],
)
def test_safe_paths_allowed(path: str, home: Path) -> None:
    rc, err = _single(path, home)
    assert rc == 0
    assert err == ""


# ---------------------------------------------------------------------------
# Default protected patterns — must exit 2 with BLOCKED message
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    [
        # .env variants
        ".env",
        "backend/.env",
        ".env.local",
        ".env.production",
        # secrets directory
        "secrets/api.json",
        "config/secrets/db.json",
        # secret files
        "secret.txt",
        "secrets.yaml",
        # key/cert files
        "server.key",
        "cert.pem",
        "cert.p12",
        "cert.pfx",
        # SSH keys
        ".ssh/config",
        "id_rsa",
        "/home/user/.ssh/id_rsa",
        "id_ed25519",
        "/home/user/.ssh/id_ed25519",
        # credentials / passwords
        "aws_credentials",
        "credentials.json",
        "password.txt",
        "my_password.yaml",
        # secrets suffix
        "app.secret",
        # API keys / auth tokens
        "api_key.txt",
        "api-key.json",
        "apikey.conf",
        "auth_token.env",
        "auth-token.json",
    ],
)
def test_protected_paths_blocked(path: str, home: Path) -> None:
    rc, err = _single(path, home)
    assert rc == 2, f"expected block for: {path}"
    assert "BLOCKED" in err


# ---------------------------------------------------------------------------
# Default lock file patterns — must exit 0 with WARNING message
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    [
        "package-lock.json",
        "frontend/package-lock.json",
        "yarn.lock",
        "pnpm-lock.yaml",
        "go.sum",
        "backend/go.sum",
        "Cargo.lock",
        "poetry.lock",
        "Gemfile.lock",
        "composer.lock",
    ],
)
def test_lock_files_warn_and_allow(path: str, home: Path) -> None:
    rc, err = _single(path, home)
    assert rc == 0, f"expected allow for lock file: {path}"
    assert "WARNING" in err


# ---------------------------------------------------------------------------
# Input field variants
# ---------------------------------------------------------------------------


def test_path_field_alias_blocked(home: Path) -> None:
    """tool_input.path is accepted as fallback for file_path."""
    rc, err = _run({"tool_input": {"path": ".env"}}, home)
    assert rc == 2
    assert "BLOCKED" in err


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"tool_input": {}},
        {"tool_input": {"file_path": ""}},
        {"tool_input": {"file_path": None}},
    ],
    ids=["empty", "no_file_path", "empty_string", "null"],
)
def test_missing_or_empty_path_allowed(payload: dict, home: Path) -> None:
    rc, _ = _run(payload, home)
    assert rc == 0


def test_malformed_json_allowed(home: Path) -> None:
    env = os.environ.copy()
    env["HOME"] = str(home)
    result = subprocess.run(
        [sys.executable, str(HOOK)],
        input="not-json{{{",
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0


# ---------------------------------------------------------------------------
# Codex apply_patch — custom patch format (*** headers)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "header",
    [
        "*** Update File: .env",
        "*** Add File: .env",
        "*** Delete File: .env",
    ],
)
def test_codex_patch_header_types_blocked(header: str, home: Path) -> None:
    patch = f"*** Begin Patch\n{header}\n@@ -1 +1 @@\n-old\n+new\n*** End Patch\n"
    rc, err = _patch(patch, home)
    assert rc == 2, f"expected block for patch header: {header}"
    assert "BLOCKED" in err


def test_codex_unified_diff_format_blocked(home: Path) -> None:
    patch = "--- a/.env\n+++ b/.env\n@@ -1 +1 @@\n-old\n+new\n"
    rc, err = _patch(patch, home)
    assert rc == 2
    assert "BLOCKED" in err


def test_codex_patch_safe_file_allowed(home: Path) -> None:
    patch = (
        "*** Begin Patch\n"
        "*** Update File: src/main.py\n"
        "@@ -1 +1 @@\n"
        "-old\n+new\n"
        "*** End Patch\n"
    )
    rc, err = _patch(patch, home)
    assert rc == 0
    assert err == ""


def test_codex_patch_lock_file_warns(home: Path) -> None:
    patch = (
        "*** Begin Patch\n"
        "*** Update File: go.sum\n"
        "@@ -1 +1 @@\n"
        "-old\n+new\n"
        "*** End Patch\n"
    )
    rc, err = _patch(patch, home)
    assert rc == 0
    assert "WARNING" in err


def test_codex_multi_file_patch_blocks_on_any_sensitive(home: Path) -> None:
    """Safe file + sensitive file in one patch → blocked."""
    patch = (
        "*** Begin Patch\n"
        "*** Update File: src/main.py\n"
        "@@ -1 +1 @@\n"
        "-old\n+new\n"
        "*** Update File: secrets/api.key\n"
        "@@ -1 +1 @@\n"
        "-k1\n+k2\n"
        "*** End Patch\n"
    )
    rc, err = _patch(patch, home)
    assert rc == 2
    assert "BLOCKED" in err


def test_codex_multi_file_patch_safe_allowed(home: Path) -> None:
    patch = (
        "*** Begin Patch\n"
        "*** Update File: src/a.py\n"
        "@@ -1 +1 @@\n"
        "-old\n+new\n"
        "*** Update File: src/b.py\n"
        "@@ -1 +1 @@\n"
        "-old\n+new\n"
        "*** End Patch\n"
    )
    rc, err = _patch(patch, home)
    assert rc == 0
    assert err == ""


# ---------------------------------------------------------------------------
# Custom hook-config.json overrides
# ---------------------------------------------------------------------------


def test_custom_protected_patterns_override_defaults(tmp_path: Path) -> None:
    """Custom patterns replace defaults entirely — .env is no longer blocked."""
    config = tmp_path / ".claude" / "hook-config.json"
    config.parent.mkdir()
    config.write_text(
        json.dumps(
            {
                "fileProtector": {
                    "protectedPatterns": [r"custom-secret\.txt$"],
                    "lockFilePatterns": [],
                }
            }
        )
    )
    rc, err = _run({"tool_input": {"file_path": "custom-secret.txt"}}, tmp_path)
    assert rc == 2
    assert "BLOCKED" in err

    rc, _ = _run({"tool_input": {"file_path": ".env"}}, tmp_path)
    assert rc == 0

    rc, err = _run({"tool_input": {"file_path": "package-lock.json"}}, tmp_path)
    assert rc == 0
    assert err == ""


def test_bad_regex_pattern_skipped_but_valid_patterns_still_enforced(
    tmp_path: Path,
) -> None:
    """An invalid regex must not crash the hook; remaining patterns still work."""
    config = tmp_path / ".claude" / "hook-config.json"
    config.parent.mkdir()
    config.write_text(
        json.dumps(
            {
                "fileProtector": {
                    "protectedPatterns": [r"[invalid(", r"\.env$"],
                    "lockFilePatterns": [],
                }
            }
        )
    )

    rc, err = _run({"tool_input": {"file_path": ".env"}}, tmp_path)
    assert rc == 2, f"valid pattern should still block: {err}"
    assert "BLOCKED" in err
    assert "Traceback" not in err
    assert "WARNING: Invalid regex pattern skipped" in err


def test_bad_regex_pattern_allows_non_matching_safe_path(tmp_path: Path) -> None:
    """A bad regex fails open for itself; safe paths stay unblocked."""
    config = tmp_path / ".claude" / "hook-config.json"
    config.parent.mkdir()
    config.write_text(
        json.dumps(
            {
                "fileProtector": {
                    "protectedPatterns": [r"[invalid("],
                    "lockFilePatterns": [r"[also-bad("],
                }
            }
        )
    )

    rc, err = _run({"tool_input": {"file_path": "src/main.py"}}, tmp_path)
    assert rc == 0
    assert "Traceback" not in err


def test_custom_lock_patterns_override_defaults(tmp_path: Path) -> None:
    """Custom lock patterns replace defaults — go.sum is no longer a lock file."""
    config = tmp_path / ".claude" / "hook-config.json"
    config.parent.mkdir()
    config.write_text(
        json.dumps(
            {
                "fileProtector": {
                    "protectedPatterns": [],
                    "lockFilePatterns": [r"custom\.lock$"],
                }
            }
        )
    )
    rc, err = _run({"tool_input": {"file_path": "custom.lock"}}, tmp_path)
    assert rc == 0
    assert "WARNING" in err

    rc, err = _run({"tool_input": {"file_path": "go.sum"}}, tmp_path)
    assert rc == 0
    assert err == ""
