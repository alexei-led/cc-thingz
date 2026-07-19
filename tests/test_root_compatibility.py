"""Legacy repository-root install compatibility contracts."""

from __future__ import annotations

import copy
import json
import os
import shutil
import socket
import subprocess
import time
from pathlib import Path
from typing import Any

import pytest
from conftest import REPO_ROOT

ROOT_COMPATIBILITY_FILES = (
    "package.json",
    "bun.lock",
    ".npmrc",
    ".claude-plugin/marketplace.json",
    ".agents/plugins/marketplace.json",
    ".github/plugin/marketplace.json",
    ".cursor-plugin/marketplace.json",
)


def test_root_compatibility_files_are_tracked() -> None:
    for relative in ROOT_COMPATIBILITY_FILES:
        subprocess.run(
            ["git", "ls-files", "--error-unmatch", relative],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
        )


ROOT_MARKETPLACES = {
    "claude": (
        REPO_ROOT / ".claude-plugin/marketplace.json",
        REPO_ROOT / "dist/claude/.claude-plugin/marketplace.json",
    ),
    "codex": (
        REPO_ROOT / ".agents/plugins/marketplace.json",
        REPO_ROOT / "dist/codex/.agents/plugins/marketplace.json",
    ),
    "copilot": (
        REPO_ROOT / ".github/plugin/marketplace.json",
        REPO_ROOT / "dist/copilot/.github/plugin/marketplace.json",
    ),
    "cursor": (
        REPO_ROOT / ".cursor-plugin/marketplace.json",
        REPO_ROOT / "dist/cursor/.cursor-plugin/marketplace.json",
    ),
}


def _json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _root_source(target: str, source: object) -> object:
    if isinstance(source, str):
        assert source.startswith("./")
        return f"./dist/{target}/{source.removeprefix('./')}"
    assert isinstance(source, dict)
    rewritten = copy.deepcopy(source)
    path = rewritten["path"]
    assert isinstance(path, str) and path.startswith("./")
    rewritten["path"] = f"./dist/{target}/{path.removeprefix('./')}"
    return rewritten


@pytest.mark.parametrize("target", ROOT_MARKETPLACES)
def test_root_marketplace_mirrors_generated_target(target: str) -> None:
    root_path, target_path = ROOT_MARKETPLACES[target]
    expected = copy.deepcopy(_json(target_path))
    for plugin in expected["plugins"]:
        plugin["source"] = _root_source(target, plugin["source"])

    assert _json(root_path) == expected

    for plugin in expected["plugins"]:
        source = plugin["source"]
        relative = source if isinstance(source, str) else source["path"]
        plugin_root = REPO_ROOT / relative.removeprefix("./")
        assert plugin_root.is_dir()


@pytest.mark.parametrize(
    ("target", "manifest"),
    [
        ("claude", ".claude-plugin/plugin.json"),
        ("codex", ".codex-plugin/plugin.json"),
        ("copilot", "plugin.json"),
        ("cursor", ".cursor-plugin/plugin.json"),
    ],
)
def test_root_marketplace_sources_are_installable_plugin_roots(
    target: str, manifest: str
) -> None:
    root_path, _ = ROOT_MARKETPLACES[target]
    for plugin in _json(root_path)["plugins"]:
        source = plugin["source"]
        relative = source if isinstance(source, str) else source["path"]
        assert (REPO_ROOT / relative.removeprefix("./") / manifest).is_file()


def test_root_codex_project_agents_match_generated_profiles() -> None:
    generated = REPO_ROOT / "dist/codex/.codex/agents"
    compatibility = REPO_ROOT / ".codex/agents"
    expected = {path.name: path.read_bytes() for path in generated.glob("*.toml")}
    actual = {path.name: path.read_bytes() for path in compatibility.glob("*.toml")}
    assert actual == expected


def test_root_pi_manifest_routes_to_generated_target() -> None:
    root = _json(REPO_ROOT / "package.json")
    generated = _json(REPO_ROOT / "dist/pi/package.json")

    expected_extensions = []
    for extension in generated["pi"]["extensions"]:
        if extension == "./node_modules/pi-subagents/src/extension/index.ts":
            expected_extensions.append(extension)
        else:
            expected_extensions.append(f"./dist/pi/{extension.removeprefix('./')}")

    assert root["pi"] == {
        "extensions": expected_extensions,
        "skills": ["./dist/pi/skills"],
        "subagents": {"agents": ["./dist/pi/agents"]},
    }
    assert (
        root["dependencies"]["pi-subagents"]
        == generated["dependencies"]["pi-subagents"]
    )

    for resource in (
        *root["pi"]["extensions"],
        *root["pi"]["skills"],
        *root["pi"]["subagents"]["agents"],
    ):
        assert (REPO_ROOT / resource.removeprefix("./")).exists(), resource


def test_root_npm_install_omits_pi_host_peer_dependencies(tmp_path: Path) -> None:
    shutil.copy2(REPO_ROOT / "package.json", tmp_path / "package.json")
    shutil.copy2(REPO_ROOT / ".npmrc", tmp_path / ".npmrc")
    subprocess.run(
        [
            "npm",
            "install",
            "--omit=dev",
            "--ignore-scripts",
            "--no-audit",
            "--no-fund",
        ],
        cwd=tmp_path,
        check=True,
        timeout=60,
    )
    node_modules = tmp_path / "node_modules"
    assert (node_modules / "pi-subagents").is_dir()
    assert (node_modules / "pi-subagents/node_modules/@earendil-works/pi-tui").is_dir()
    assert not (node_modules / "@earendil-works/pi-coding-agent").exists()
    assert not (node_modules / "@earendil-works/pi-ai").exists()


def _isolated_environment(tmp_path: Path) -> dict[str, str]:
    environment = os.environ.copy()
    for key in tuple(environment):
        if key.startswith("PI_SUBAGENT_"):
            environment.pop(key)
    environment.update(
        {
            "HOME": str(tmp_path / "home"),
            "CLAUDE_CONFIG_DIR": str(tmp_path / "claude"),
            "CODEX_HOME": str(tmp_path / "codex"),
            "PI_CODING_AGENT_DIR": str(tmp_path / "pi-agent"),
            "XDG_CACHE_HOME": str(tmp_path / "cache"),
            "XDG_CONFIG_HOME": str(tmp_path / "config"),
            "PI_OFFLINE": "1",
        }
    )
    for key in (
        "HOME",
        "CLAUDE_CONFIG_DIR",
        "CODEX_HOME",
        "PI_CODING_AGENT_DIR",
        "XDG_CACHE_HOME",
        "XDG_CONFIG_HOME",
    ):
        Path(environment[key]).mkdir(parents=True, exist_ok=True)
    return environment


@pytest.mark.parametrize(
    ("target", "command"),
    [
        ("claude", ("plugin", "marketplace", "add")),
        ("codex", ("plugin", "marketplace", "add")),
        ("copilot", ("plugin", "marketplace", "add")),
        ("grok", ("plugin", "marketplace", "add")),
    ],
)
def test_repository_root_marketplace_registers_from_local_path(
    tmp_path: Path, target: str, command: tuple[str, ...]
) -> None:
    executable = shutil.which(target)
    if executable is None:
        pytest.skip(f"{target} CLI is not installed")

    environment = _isolated_environment(tmp_path)
    project = tmp_path / "project"
    project.mkdir()
    arguments = [executable, *command, str(REPO_ROOT)]
    if target == "codex":
        arguments.append("--json")
    subprocess.run(
        arguments,
        cwd=project,
        env=environment,
        check=True,
        timeout=30,
    )

    install_commands = {
        "claude": [
            executable,
            "plugin",
            "install",
            "browser@cc-thingz",
            "--scope",
            "local",
        ],
        "codex": [
            executable,
            "plugin",
            "add",
            "browser@cc-thingz",
            "--json",
        ],
        "copilot": [
            executable,
            "plugin",
            "install",
            "browser@cc-thingz",
        ],
        "grok": [
            executable,
            "plugin",
            "install",
            str(REPO_ROOT / "dist/claude/browser"),
            "--trust",
        ],
    }
    subprocess.run(
        install_commands[target],
        cwd=project,
        env=environment,
        check=True,
        timeout=30,
    )


def test_repository_root_pi_package_loads_commands_from_local_path(
    tmp_path: Path,
) -> None:
    pi = shutil.which("pi")
    if pi is None:
        pytest.skip("Pi CLI is not installed")

    project = tmp_path / "project"
    project.mkdir()
    environment = _isolated_environment(tmp_path)
    subprocess.run(
        [pi, "install", str(REPO_ROOT), "--approve"],
        cwd=project,
        env=environment,
        check=True,
        timeout=30,
    )
    rpc = subprocess.run(
        [pi, "--mode", "rpc", "--no-session"],
        cwd=project,
        env=environment,
        input='{"type":"get_commands"}\n',
        capture_output=True,
        check=True,
        text=True,
        timeout=30,
    )
    responses = [json.loads(line) for line in rpc.stdout.splitlines() if line.strip()]
    commands = next(
        response["data"]["commands"]
        for response in responses
        if response.get("type") == "response"
        and response.get("command") == "get_commands"
    )
    names = {command["name"] for command in commands}
    assert {"plan", "todos", "subagents-doctor", "skill:fixing-code"} <= names
    fixing_code = next(
        command for command in commands if command["name"] == "skill:fixing-code"
    )
    assert "/dist/pi/skills/fixing-code/SKILL.md" in fixing_code["sourceInfo"]["path"]


def test_repository_root_pi_package_loads_from_git_checkout(tmp_path: Path) -> None:
    pi = shutil.which("pi")
    if pi is None:
        pytest.skip("Pi CLI is not installed")

    source = tmp_path / "source"
    subprocess.run(
        ["git", "clone", "--quiet", "--no-local", str(REPO_ROOT), str(source)],
        check=True,
    )
    bare = tmp_path / "test/cc-thingz.git"
    bare.parent.mkdir()
    subprocess.run(
        ["git", "clone", "--quiet", "--bare", str(source), str(bare)],
        check=True,
    )
    subprocess.run(["git", "-C", str(bare), "update-server-info"], check=True)

    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    server = subprocess.Popen(
        [
            "python3",
            "-m",
            "http.server",
            str(port),
            "--bind",
            "127.0.0.1",
            "--directory",
            str(tmp_path),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        time.sleep(0.2)
        environment = _isolated_environment(tmp_path / "git-install")
        environment.pop("PI_OFFLINE")
        environment["GIT_TERMINAL_PROMPT"] = "0"
        subprocess.run(
            [
                pi,
                "install",
                f"http://127.0.0.1:{port}/test/cc-thingz.git",
                "--approve",
            ],
            env=environment,
            check=True,
            timeout=180,
        )

        clone = (
            Path(environment["PI_CODING_AGENT_DIR"]) / "git/127.0.0.1/test/cc-thingz"
        )
        assert (clone / "node_modules/pi-subagents/src/extension/index.ts").is_file()
        assert (
            clone / "node_modules/pi-subagents/node_modules/@earendil-works/pi-tui"
        ).is_dir()
        assert not (clone / "node_modules/@earendil-works/pi-coding-agent").exists()
        rpc = subprocess.run(
            [pi, "--mode", "rpc", "--no-session"],
            env=environment,
            input='{"type":"get_commands"}\n',
            capture_output=True,
            check=True,
            text=True,
            timeout=30,
        )
        responses = [
            json.loads(line) for line in rpc.stdout.splitlines() if line.strip()
        ]
        commands = next(
            response["data"]["commands"]
            for response in responses
            if response.get("type") == "response"
            and response.get("command") == "get_commands"
        )
        assert {
            "plan",
            "todos",
            "subagents-doctor",
            "skill:fixing-code",
        } <= {command["name"] for command in commands}
    finally:
        server.terminate()
        server.wait(timeout=5)
