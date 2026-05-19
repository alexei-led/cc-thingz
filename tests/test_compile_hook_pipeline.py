"""Tests for `scripts.build.compile_hook` (Task 10).

Covers:

- HookSpec loading from `meta.yaml` + lone `hook.*` resolution and validation
- Script placement per target (flat vs plugin-grouped) with mode preservation
- Support-dir mirroring alongside the script
- Gemini aggregated `hooks.json` shape (BeforeTool/AfterTool/AfterAgent/
  SessionStart, `${extensionPath}/hooks/<script>` substitution)
- Codex per-plugin `hooks.json` shape (PreToolUse/PostToolUse/Stop/
  SessionStart, `$PLUGIN_ROOT/hooks/<script>` substitution, statusMessage)
- Claude per-plugin `hooks.json` shape (PreToolUse/PostToolUse/Stop/
  SessionStart, `${CLAUDE_PLUGIN_ROOT}/hooks/<script>` substitution)
- Pi manifest generated from meta.yaml + merged with hooks-external.json
- CC-only events (worktreecreate, worktreeremove) are dropped from
  Gemini/Codex manifests
"""

from __future__ import annotations

import json
import stat
from pathlib import Path

import pytest
from conftest import REPO_ROOT


@pytest.fixture(scope="module")
def ch(load_script):
    """Load `compile_hook.py` via the shared loader (compile.py must come first)."""
    load_script("build/compile.py")
    return load_script("build/compile_hook.py")


def _write_hook(
    src: Path,
    name: str,
    event: str,
    *,
    timeout: int = 10,
    status_message: str | None = None,
    ext: str = ".sh",
    body: str = "#!/usr/bin/env bash\nexit 0\n",
    executable: bool = True,
    support_dirs: dict[str, dict[str, str]] | None = None,
    targets: list[str] | None = None,
) -> Path:
    """Build a `src/hooks/<name>/` source tree under `src` and return its path."""
    hook_dir = src / "hooks" / name
    hook_dir.mkdir(parents=True)
    meta_lines = [f"name: {name}", f"event: {event}", f"timeout: {timeout}"]
    if status_message is not None:
        meta_lines.append(f"status_message: {status_message}")
    if targets is not None:
        meta_lines.append("targets:")
        meta_lines.extend(f"  - {target}" for target in targets)
    (hook_dir / "meta.yaml").write_text("\n".join(meta_lines) + "\n")
    script = hook_dir / f"hook{ext}"
    script.write_text(body)
    if executable:
        script.chmod(script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP)
    for dir_name, files in (support_dirs or {}).items():
        sub = hook_dir / dir_name
        sub.mkdir()
        for fname, content in files.items():
            (sub / fname).write_text(content)
    return hook_dir


# --- HookSpec loading -------------------------------------------------------


def test_load_hook_minimal(ch, tmp_path):
    hook_dir = _write_hook(tmp_path / "src", "smart-lint", "postedit", timeout=60)
    spec = ch.load_hook(hook_dir)
    assert spec.name == "smart-lint"
    assert spec.event == "postedit"
    assert spec.timeout == 60
    assert spec.script_basename == "smart-lint.sh"
    assert spec.status_message is None


def test_load_hook_with_status_message(ch, tmp_path):
    hook_dir = _write_hook(
        tmp_path / "src",
        "session-start",
        "sessionstart",
        timeout=5,
        status_message="Loading context",
        ext=".py",
        body="#!/usr/bin/env python3\n",
    )
    spec = ch.load_hook(hook_dir)
    assert spec.script_basename == "session-start.py"
    assert spec.status_message == "Loading context"


def test_load_hook_missing_meta(ch, tmp_path):
    hook_dir = tmp_path / "src" / "hooks" / "broken"
    hook_dir.mkdir(parents=True)
    (hook_dir / "hook.sh").write_text("#!/bin/sh\n")
    with pytest.raises(FileNotFoundError, match="meta.yaml"):
        ch.load_hook(hook_dir)


def test_load_hook_missing_script(ch, tmp_path):
    hook_dir = tmp_path / "src" / "hooks" / "no-script"
    hook_dir.mkdir(parents=True)
    (hook_dir / "meta.yaml").write_text("name: x\nevent: postedit\ntimeout: 1\n")
    with pytest.raises(FileNotFoundError, match="hook"):
        ch.load_hook(hook_dir)


def test_load_hook_multiple_scripts(ch, tmp_path):
    hook_dir = tmp_path / "src" / "hooks" / "dup"
    hook_dir.mkdir(parents=True)
    (hook_dir / "meta.yaml").write_text("name: dup\nevent: postedit\ntimeout: 1\n")
    (hook_dir / "hook.sh").write_text("#!/bin/sh\n")
    (hook_dir / "hook.py").write_text("#!/usr/bin/env python3\n")
    with pytest.raises(ValueError, match="multiple"):
        ch.load_hook(hook_dir)


def test_load_hook_unknown_event(ch, tmp_path):
    hook_dir = tmp_path / "src" / "hooks" / "weird"
    hook_dir.mkdir(parents=True)
    (hook_dir / "meta.yaml").write_text("name: weird\nevent: madeup\ntimeout: 1\n")
    (hook_dir / "hook.sh").write_text("#!/bin/sh\n")
    with pytest.raises(ValueError, match="unknown event"):
        ch.load_hook(hook_dir)


def test_load_hook_missing_required_field(ch, tmp_path):
    hook_dir = tmp_path / "src" / "hooks" / "partial"
    hook_dir.mkdir(parents=True)
    (hook_dir / "meta.yaml").write_text("name: partial\nevent: postedit\n")
    (hook_dir / "hook.sh").write_text("#!/bin/sh\n")
    with pytest.raises(ValueError, match="timeout"):
        ch.load_hook(hook_dir)


@pytest.mark.parametrize(
    "bad_name",
    ["../escape", "has space", "../../etc/passwd", "with/slash", "-leading-dash", ""],
)
def test_load_hook_rejects_unsafe_names(ch, tmp_path, bad_name):
    hook_dir = tmp_path / "src" / "hooks" / "h"
    hook_dir.mkdir(parents=True)
    (hook_dir / "meta.yaml").write_text(
        f"name: {bad_name!r}\nevent: postedit\ntimeout: 10\n"
    )
    (hook_dir / "hook.sh").write_text("#!/bin/sh\n")
    with pytest.raises(ValueError, match="name"):
        ch.load_hook(hook_dir)


@pytest.mark.parametrize(
    "targets_yaml",
    ["targets: pi", "targets: 1", "targets:\n  - pi\n  - 2"],
)
def test_load_hook_rejects_malformed_targets(ch, tmp_path, targets_yaml):
    hook_dir = tmp_path / "src" / "hooks" / "bad-targets"
    hook_dir.mkdir(parents=True)
    (hook_dir / "meta.yaml").write_text(
        f"name: bad-targets\nevent: postedit\ntimeout: 10\n{targets_yaml}\n"
    )
    (hook_dir / "hook.sh").write_text("#!/bin/sh\n")
    with pytest.raises(ValueError, match="targets"):
        ch.load_hook(hook_dir)


def test_load_hook_rejects_unknown_targets(ch, tmp_path):
    hook_dir = tmp_path / "src" / "hooks" / "unknown-target"
    hook_dir.mkdir(parents=True)
    (hook_dir / "meta.yaml").write_text(
        "name: unknown-target\nevent: postedit\ntimeout: 10\ntargets:\n  - nope\n"
    )
    (hook_dir / "hook.sh").write_text("#!/bin/sh\n")
    with pytest.raises(ValueError, match="unknown targets"):
        ch.load_hook(hook_dir)


# --- compile_hook (placement) ----------------------------------------------


def test_compile_hook_flat_target_pi(ch, tmp_path):
    src = tmp_path / "src"
    hook_dir = _write_hook(src, "smart-lint", "postedit", timeout=60)
    result = ch.compile_hook(hook_dir, "pi", {}, tmp_path)
    assert len(result.placements) == 1
    dest, plugin = result.placements[0]
    assert dest == tmp_path / "dist" / "pi" / "hooks" / "smart-lint.sh"
    assert dest.is_file()
    assert plugin is None
    # Mode preserved (executable bit).
    assert dest.stat().st_mode & stat.S_IXUSR


def test_compile_hook_flat_target_gemini(ch, tmp_path):
    src = tmp_path / "src"
    hook_dir = _write_hook(src, "smart-lint", "postedit")
    result = ch.compile_hook(hook_dir, "gemini", {}, tmp_path)
    assert result.placements[0][0] == (
        tmp_path / "dist" / "gemini" / "hooks" / "smart-lint.sh"
    )


def test_compile_hook_plugin_grouped_with_index(ch, tmp_path):
    src = tmp_path / "src"
    hook_dir = _write_hook(src, "smart-lint", "postedit")
    plugin_index = {"smart-lint": ["dev-workflow", "go-dev"]}
    result = ch.compile_hook(hook_dir, "codex", plugin_index, tmp_path)
    paths = {p[0]: p[1] for p in result.placements}
    assert (
        tmp_path
        / "dist"
        / "codex"
        / "plugins"
        / "dev-workflow"
        / "hooks"
        / "smart-lint.sh"
    ) in paths
    assert (
        tmp_path / "dist" / "codex" / "plugins" / "go-dev" / "hooks" / "smart-lint.sh"
    ) in paths
    assert set(paths.values()) == {"dev-workflow", "go-dev"}


def test_compile_hook_plugin_grouped_empty_index_falls_back_flat(ch, tmp_path):
    src = tmp_path / "src"
    hook_dir = _write_hook(src, "smart-lint", "postedit")
    result = ch.compile_hook(hook_dir, "codex", {}, tmp_path)
    assert len(result.placements) == 1
    dest, plugin = result.placements[0]
    assert dest == tmp_path / "dist" / "codex" / "hooks" / "smart-lint.sh"
    assert plugin is None


def test_compile_hook_copies_support_dir(ch, tmp_path):
    src = tmp_path / "src"
    hook_dir = _write_hook(
        src,
        "smart-lint",
        "postedit",
        support_dirs={"smart-lint": {"linter.sh": "#!/bin/sh\necho lint\n"}},
    )
    ch.compile_hook(hook_dir, "pi", {}, tmp_path)
    helper = tmp_path / "dist" / "pi" / "hooks" / "smart-lint" / "linter.sh"
    assert helper.is_file()
    assert helper.read_text() == "#!/bin/sh\necho lint\n"


def test_compile_hook_ignores_target_subdirs(ch, tmp_path):
    src = tmp_path / "src"
    hook_dir = _write_hook(src, "smart-lint", "postedit")
    # Add a stray target-named subdir; must NOT be copied as support.
    (hook_dir / "claude").mkdir()
    (hook_dir / "claude" / "extra.txt").write_text("CC-only stuff")
    ch.compile_hook(hook_dir, "pi", {}, tmp_path)
    leaked = tmp_path / "dist" / "pi" / "hooks" / "claude"
    assert not leaked.exists()


def test_compile_hook_honors_targets_restriction(ch, tmp_path):
    src = tmp_path / "src"
    hook_dir = _write_hook(src, "pi-only", "exitplanmode", targets=["pi"])
    skipped = ch.compile_hook(hook_dir, "claude", {}, tmp_path)
    assert skipped.placements == []
    assert not (tmp_path / "dist" / "claude" / "hooks" / "pi-only.sh").exists()

    result = ch.compile_hook(hook_dir, "pi", {}, tmp_path)
    assert result.placements[0][0] == tmp_path / "dist" / "pi" / "hooks" / "pi-only.sh"


# --- manifest building (Gemini) --------------------------------------------


def _compile_all(ch, hook_dirs, target, plugin_index, root):
    return [ch.compile_hook(h, target, plugin_index, root) for h in hook_dirs]


def test_gemini_manifest_aggregates_events(ch, tmp_path):
    src = tmp_path / "src"
    h_pre = _write_hook(src, "file-protector", "preedit", timeout=10)
    h_post = _write_hook(src, "smart-lint", "postedit", timeout=60)
    h_stop = _write_hook(src, "test-runner", "agentstop", timeout=60)
    h_session = _write_hook(src, "session-start", "sessionstart", timeout=5)
    results = _compile_all(
        ch, [h_pre, h_post, h_stop, h_session], "gemini", {}, tmp_path
    )
    written = ch.write_hook_manifests(results, "gemini", tmp_path)
    assert len(written) == 1
    manifest = json.loads(written[0].read_text())

    events = manifest["hooks"]
    assert set(events) == {"BeforeTool", "AfterTool", "SessionStart", "AfterAgent"}

    # BeforeTool: write_file|replace matcher present, sequential=True
    before = events["BeforeTool"][0]
    assert before["matcher"] == "write_file|replace"
    assert before["sequential"] is True
    assert before["hooks"][0]["command"] == "${extensionPath}/hooks/file-protector.sh"
    assert before["hooks"][0]["timeout"] == 10_000

    # AfterTool: write_file|replace matcher present
    after = events["AfterTool"][0]
    assert after["matcher"] == "write_file|replace"
    assert after["sequential"] is True
    assert after["hooks"][0]["name"] == "smart-lint"
    assert after["hooks"][0]["timeout"] == 60_000

    # SessionStart: no matcher key, no sequential key
    session = events["SessionStart"][0]
    assert "matcher" not in session
    assert "sequential" not in session
    assert session["hooks"][0]["command"] == "${extensionPath}/hooks/session-start.sh"

    after_agent = events["AfterAgent"][0]
    assert "matcher" not in after_agent
    assert "sequential" not in after_agent
    assert after_agent["hooks"][0]["command"] == "${extensionPath}/hooks/test-runner.sh"


def test_gemini_manifest_drops_cc_only_events(ch, tmp_path):
    src = tmp_path / "src"
    h_wt = _write_hook(src, "worktree-create", "worktreecreate")
    results = _compile_all(ch, [h_wt], "gemini", {}, tmp_path)
    written = ch.write_hook_manifests(results, "gemini", tmp_path)
    assert written == []
    assert not (tmp_path / "dist" / "gemini" / "hooks" / "hooks.json").exists()


def test_gemini_manifest_notification_event(ch, tmp_path):
    src = tmp_path / "src"
    hook = _write_hook(src, "notify", "notification")
    results = _compile_all(ch, [hook], "gemini", {}, tmp_path)
    written = ch.write_hook_manifests(results, "gemini", tmp_path)
    assert len(written) == 1
    manifest = json.loads(written[0].read_text())
    assert "Notification" in manifest["hooks"]
    notif = manifest["hooks"]["Notification"][0]
    assert notif["hooks"][0]["name"] == "notify"


def test_gemini_manifest_prebash_routes_to_run_shell_command(ch, tmp_path):
    src = tmp_path / "src"
    hook = _write_hook(src, "git-guardrails", "prebash")
    results = _compile_all(ch, [hook], "gemini", {}, tmp_path)
    written = ch.write_hook_manifests(results, "gemini", tmp_path)
    manifest = json.loads(written[0].read_text())
    before = manifest["hooks"]["BeforeTool"][0]
    assert before["matcher"] == "run_shell_command"


# --- manifest building (Codex) ---------------------------------------------


def test_codex_manifest_per_plugin(ch, tmp_path):
    src = tmp_path / "src"
    h_prebash = _write_hook(
        src,
        "git-guardrails",
        "prebash",
        timeout=10,
        status_message="Checking git",
    )
    h_post = _write_hook(src, "smart-lint", "postedit", timeout=60)
    h_stop = _write_hook(src, "test-runner", "agentstop", timeout=60)
    plugin_index = {
        "git-guardrails": ["dev-workflow"],
        "smart-lint": ["dev-workflow"],
        "test-runner": ["dev-workflow"],
    }
    results = _compile_all(
        ch, [h_prebash, h_post, h_stop], "codex", plugin_index, tmp_path
    )
    written = ch.write_hook_manifests(results, "codex", tmp_path)
    assert len(written) == 1
    assert written[0] == (
        tmp_path
        / "dist"
        / "codex"
        / "plugins"
        / "dev-workflow"
        / "hooks"
        / "hooks.json"
    )
    manifest = json.loads(written[0].read_text())
    assert set(manifest["hooks"]) == {"PreToolUse", "PostToolUse", "Stop"}

    pre = manifest["hooks"]["PreToolUse"][0]
    assert pre["matcher"] == "^Bash$"
    assert pre["hooks"][0]["command"] == '"$PLUGIN_ROOT/hooks/git-guardrails.sh"'
    assert pre["hooks"][0]["timeout"] == 10
    assert pre["hooks"][0]["statusMessage"] == "Checking git"

    post = manifest["hooks"]["PostToolUse"][0]
    assert post["matcher"] == "^apply_patch$"
    assert "statusMessage" not in post["hooks"][0]

    stop = manifest["hooks"]["Stop"][0]
    assert "matcher" not in stop
    assert stop["hooks"][0]["command"] == '"$PLUGIN_ROOT/hooks/test-runner.sh"'


def test_codex_manifest_skips_when_no_plugin(ch, tmp_path):
    """With empty plugin_index, codex hooks land at flat fallback (no manifest)."""
    src = tmp_path / "src"
    hook = _write_hook(src, "smart-lint", "postedit")
    results = _compile_all(ch, [hook], "codex", {}, tmp_path)
    written = ch.write_hook_manifests(results, "codex", tmp_path)
    assert written == []


def test_codex_manifest_drops_cc_only_events(ch, tmp_path):
    src = tmp_path / "src"
    # preedit → PreToolUse/apply_patch (codex); userpromptsubmit/notification → None.
    h_pre = _write_hook(src, "file-protector", "preedit")
    h_ups = _write_hook(src, "skill-enforcer", "userpromptsubmit")
    h_notif = _write_hook(src, "notify", "notification")
    plugin_index = {
        "file-protector": ["dev-workflow"],
        "skill-enforcer": ["dev-workflow"],
        "notify": ["dev-workflow"],
    }
    results = _compile_all(ch, [h_pre, h_ups, h_notif], "codex", plugin_index, tmp_path)
    written = ch.write_hook_manifests(results, "codex", tmp_path)
    # userpromptsubmit and notification are None for codex; preedit emits a manifest.
    assert len(written) == 1
    manifest = json.loads(written[0].read_text())
    assert "PreToolUse" in manifest["hooks"]
    assert manifest["hooks"]["PreToolUse"][0]["matcher"] == "^apply_patch$"


def test_codex_manifest_multi_plugin(ch, tmp_path):
    src = tmp_path / "src"
    hook = _write_hook(src, "smart-lint", "postedit", timeout=60)
    plugin_index = {"smart-lint": ["plugin-a", "plugin-b"]}
    results = _compile_all(ch, [hook], "codex", plugin_index, tmp_path)
    written = ch.write_hook_manifests(results, "codex", tmp_path)
    assert len(written) == 2
    plugin_names = {p.parent.parent.name for p in written}
    assert plugin_names == {"plugin-a", "plugin-b"}


# --- manifest building (Claude / Pi) ---------------------------------------


def test_claude_manifest_per_plugin(ch, tmp_path):
    src = tmp_path / "src"
    h_pre = _write_hook(src, "file-protector", "preedit", timeout=10)
    h_prebash = _write_hook(src, "git-guardrails", "prebash", timeout=10)
    h_post = _write_hook(src, "smart-lint", "postedit", timeout=60)
    h_stop = _write_hook(src, "test-runner", "agentstop", timeout=60)
    h_notify = _write_hook(src, "notify", "notification", timeout=10)
    h_session = _write_hook(src, "session-start", "sessionstart", timeout=5)
    h_ups = _write_hook(src, "skill-enforcer", "userpromptsubmit", timeout=15)
    plugin_index = {
        "file-protector": ["dev-workflow"],
        "git-guardrails": ["dev-workflow"],
        "smart-lint": ["dev-workflow"],
        "test-runner": ["dev-workflow"],
        "notify": ["dev-workflow"],
        "session-start": ["dev-workflow"],
        "skill-enforcer": ["dev-workflow"],
    }
    results = _compile_all(
        ch,
        [h_pre, h_prebash, h_post, h_stop, h_notify, h_session, h_ups],
        "claude",
        plugin_index,
        tmp_path,
    )
    written = ch.write_hook_manifests(results, "claude", tmp_path)
    assert written == [
        tmp_path
        / "dist"
        / "claude"
        / "plugins"
        / "dev-workflow"
        / "hooks"
        / "hooks.json"
    ]
    manifest = json.loads(written[0].read_text())
    events = manifest["hooks"]
    assert set(events) == {
        "SessionStart",
        "UserPromptSubmit",
        "PreToolUse",
        "PostToolUse",
        "Notification",
        "Stop",
    }

    session = events["SessionStart"][0]
    assert "matcher" not in session
    assert session["hooks"][0]["command"] == (
        "${CLAUDE_PLUGIN_ROOT}/hooks/session-start.sh"
    )

    pre_groups = {g["matcher"]: g for g in events["PreToolUse"]}
    assert pre_groups["Write|Edit|MultiEdit"]["hooks"][0]["command"] == (
        "${CLAUDE_PLUGIN_ROOT}/hooks/file-protector.sh"
    )
    assert pre_groups["Bash"]["hooks"][0]["command"] == (
        "${CLAUDE_PLUGIN_ROOT}/hooks/git-guardrails.sh"
    )

    post = events["PostToolUse"][0]
    assert post["matcher"] == "Write|Edit|MultiEdit"
    assert post["hooks"][0]["command"] == ("${CLAUDE_PLUGIN_ROOT}/hooks/smart-lint.sh")
    assert post["hooks"][0]["timeout"] == 60

    stop = events["Stop"][0]
    assert "matcher" not in stop
    assert stop["hooks"][0]["command"] == ("${CLAUDE_PLUGIN_ROOT}/hooks/test-runner.sh")


def test_claude_manifest_skips_when_no_plugin(ch, tmp_path):
    src = tmp_path / "src"
    hook = _write_hook(src, "smart-lint", "postedit")
    results = _compile_all(ch, [hook], "claude", {}, tmp_path)
    written = ch.write_hook_manifests(results, "claude", tmp_path)
    assert written == []


def test_pi_manifest_from_meta_yaml(ch, tmp_path):
    """Pi hooks.json is generated from meta.yaml — no hand-maintained file."""
    src = tmp_path / "src"
    hook = _write_hook(src, "smart-lint", "postedit", timeout=60)
    results = _compile_all(ch, [hook], "pi", {}, tmp_path)
    written = ch.write_hook_manifests(results, "pi", tmp_path)
    assert len(written) == 1
    manifest_path = written[0]
    assert manifest_path == tmp_path / "dist" / "pi" / "extensions" / "hooks.json"
    manifest = json.loads(manifest_path.read_text())
    post = manifest["hooks"]["PostToolUse"][0]
    assert post["matcher"] == "Write|Edit|MultiEdit"
    assert post["hooks"][0]["command"] == "${PI_HOOKS_DIR}/smart-lint.sh"
    assert post["hooks"][0]["timeout"] == 60
    assert "async" not in post["hooks"][0]


def test_pi_manifest_merges_external(ch, tmp_path):
    """Pi hooks.json merges entries from src/pi-extensions/hooks-external.json."""
    src = tmp_path / "src"
    hook = _write_hook(src, "smart-lint", "postedit")
    build_dir = tmp_path / "scripts" / "build"
    build_dir.mkdir(parents=True, exist_ok=True)
    (build_dir / "pi-hooks-external.json").write_text(
        json.dumps(
            {
                "hooks": {
                    "SessionStart": [
                        {
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": "ccgram hook",
                                    "timeout": 5,
                                    "async": True,
                                }
                            ]
                        }
                    ]
                }
            }
        )
    )
    results = _compile_all(ch, [hook], "pi", {}, tmp_path)
    written = ch.write_hook_manifests(results, "pi", tmp_path)
    assert len(written) == 1
    manifest = json.loads(written[0].read_text())
    assert "SessionStart" in manifest["hooks"]
    assert manifest["hooks"]["SessionStart"][0]["hooks"][0]["command"] == "ccgram hook"


def test_pi_manifest_honors_pi_async(ch, tmp_path):
    """meta.yaml `pi: { async: true }` flows through to the Pi entry."""
    src = tmp_path / "src"
    hook_dir = src / "hooks" / "async-lint"
    hook_dir.mkdir(parents=True, exist_ok=True)
    (hook_dir / "hook.sh").write_text("#!/bin/sh\nexit 0\n")
    (hook_dir / "meta.yaml").write_text(
        "name: async-lint\nevent: postedit\ntimeout: 120\npi:\n  async: true\n"
    )
    spec = ch.load_hook(hook_dir)
    assert spec.pi_async is True
    results = _compile_all(ch, [hook_dir], "pi", {}, tmp_path)
    written = ch.write_hook_manifests(results, "pi", tmp_path)
    manifest = json.loads(written[0].read_text())
    entry = manifest["hooks"]["PostToolUse"][0]["hooks"][0]
    assert entry["async"] is True


def test_pi_manifest_agentstop_routes_to_stop(ch, tmp_path):
    src = tmp_path / "src"
    hook = _write_hook(src, "test-runner", "agentstop", timeout=60)
    results = _compile_all(ch, [hook], "pi", {}, tmp_path)
    written = ch.write_hook_manifests(results, "pi", tmp_path)
    manifest = json.loads(written[0].read_text())
    stop = manifest["hooks"]["Stop"][0]
    assert "matcher" not in stop
    assert stop["hooks"][0]["command"] == "${PI_HOOKS_DIR}/test-runner.sh"


def test_pi_manifest_fails_loud_when_event_missing_from_order(
    ch, tmp_path, monkeypatch
):
    """Adding a new Pi-mapped event without updating PI_EVENT_ORDER must
    surface as a build failure, not silently drop the hook."""
    monkeypatch.setitem(
        ch.EVENT_MAP,
        "rogueevent",
        {"pi": ("RogueEvent", None), "claude": None, "codex": None, "gemini": None},
    )
    src = tmp_path / "src"
    hook_dir = src / "hooks" / "rogue"
    hook_dir.mkdir(parents=True)
    (hook_dir / "hook.sh").write_text("#!/bin/sh\nexit 0\n")
    (hook_dir / "meta.yaml").write_text("name: rogue\nevent: rogueevent\ntimeout: 10\n")
    spec = ch.load_hook(hook_dir)
    with pytest.raises(ValueError, match="PI_EVENT_ORDER"):
        ch._build_pi([spec])


def test_pi_manifest_external_only_when_all_meta_hooks_restricted(ch, tmp_path):
    """External-only path: every meta.yaml hook is `targets`-restricted away from Pi,
    but `pi-hooks-external.json` still contributes entries — the Pi manifest must
    still be written from the external alone."""
    src = tmp_path / "src"
    # Hook restricted to claude only — no Pi placement.
    hook = _write_hook(src, "claude-only", "postedit", targets=["claude"])
    build_dir = tmp_path / "scripts" / "build"
    build_dir.mkdir(parents=True, exist_ok=True)
    (build_dir / "pi-hooks-external.json").write_text(
        json.dumps(
            {
                "hooks": {
                    "SessionStart": [
                        {
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": "ccgram hook",
                                    "timeout": 5,
                                    "async": True,
                                }
                            ]
                        }
                    ]
                }
            }
        )
    )
    results = _compile_all(ch, [hook], "pi", {}, tmp_path)
    written = ch.write_hook_manifests(results, "pi", tmp_path)
    assert len(written) == 1
    manifest = json.loads(written[0].read_text())
    assert list(manifest["hooks"].keys()) == ["SessionStart"]
    assert manifest["hooks"]["SessionStart"][0]["hooks"][0]["command"] == "ccgram hook"


def test_pi_manifest_honors_pi_timeout_override(ch, tmp_path):
    """meta.yaml `pi: { timeout: N }` overrides the default `timeout` for Pi only."""
    src = tmp_path / "src"
    hook_dir = src / "hooks" / "revdiff-plan-review"
    hook_dir.mkdir(parents=True, exist_ok=True)
    (hook_dir / "hook.py").write_text("#!/usr/bin/env python3\n")
    (hook_dir / "meta.yaml").write_text(
        "name: revdiff-plan-review\n"
        "event: exitplanmode\n"
        "timeout: 345600\n"
        "pi:\n"
        "  timeout: 1740\n"
    )
    spec = ch.load_hook(hook_dir)
    assert spec.timeout == 345600
    assert spec.pi_timeout == 1740
    assert spec.effective_pi_timeout == 1740
    results = _compile_all(ch, [hook_dir], "pi", {}, tmp_path)
    written = ch.write_hook_manifests(results, "pi", tmp_path)
    manifest = json.loads(written[0].read_text())
    entry = manifest["hooks"]["PreToolUse"][0]["hooks"][0]
    assert entry["timeout"] == 1740


# --- end-to-end smoke -------------------------------------------------------


def test_real_src_hooks_compile(ch):
    """Smoke: every src/hooks/<name>/ loads cleanly."""
    hook_root = REPO_ROOT / "src" / "hooks"
    if not hook_root.is_dir():
        pytest.skip("src/hooks not present")
    hooks = sorted(p for p in hook_root.iterdir() if p.is_dir())
    assert hooks, "expected migrated hooks under src/hooks/"
    for hook_dir in hooks:
        spec = ch.load_hook(hook_dir)
        assert spec.name == hook_dir.name
        assert spec.event in ch.EVENT_MAP


def test_real_src_hooks_gemini_manifest(ch, tmp_path):
    """End-to-end: compile every real hook for Gemini and inspect the manifest."""
    hook_root = REPO_ROOT / "src" / "hooks"
    if not hook_root.is_dir():
        pytest.skip("src/hooks not present")
    hooks = sorted(p for p in hook_root.iterdir() if p.is_dir())
    results = [ch.compile_hook(h, "gemini", {}, tmp_path) for h in hooks]
    written = ch.write_hook_manifests(results, "gemini", tmp_path)
    if not written:
        pytest.skip("no Gemini-mappable events in real hooks")
    manifest = json.loads(written[0].read_text())
    assert "hooks" in manifest
    for event in manifest["hooks"]:
        assert event in ch.GEMINI_EVENT_ORDER


def test_real_src_hooks_claude_manifest(ch, tmp_path):
    """End-to-end: compile every real hook for Claude and inspect plugin manifests."""
    hook_root = REPO_ROOT / "src" / "hooks"
    if not hook_root.is_dir():
        pytest.skip("src/hooks not present")
    hooks = sorted(p for p in hook_root.iterdir() if p.is_dir())
    plugin_index = {
        "file-protector": ["dev-workflow"],
        "git-guardrails": ["dev-workflow"],
        "notify": ["dev-workflow"],
        "session-start": ["dev-workflow"],
        "skill-enforcer": ["dev-workflow"],
        "smart-lint": ["dev-workflow"],
        "test-runner": ["dev-workflow"],
        "worktree-create": ["dev-tools"],
        "worktree-remove": ["dev-tools"],
    }
    results = [ch.compile_hook(h, "claude", plugin_index, tmp_path) for h in hooks]
    written = ch.write_hook_manifests(results, "claude", tmp_path)
    assert {p.parent.parent.name for p in written} == {"dev-workflow", "dev-tools"}

    by_plugin = {p.parent.parent.name: json.loads(p.read_text()) for p in written}
    assert "PreToolUse" in by_plugin["dev-workflow"]["hooks"]
    assert "PostToolUse" in by_plugin["dev-workflow"]["hooks"]
    assert "Stop" in by_plugin["dev-workflow"]["hooks"]
    assert "WorktreeCreate" in by_plugin["dev-tools"]["hooks"]
    assert "WorktreeRemove" in by_plugin["dev-tools"]["hooks"]
