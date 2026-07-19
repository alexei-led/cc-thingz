"""Distribution and release contracts for Agent Bundler output."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tarfile
import tomllib
from pathlib import Path

import frontmatter
import pytest
from conftest import REPO_ROOT

TARGETS = ("claude", "codex", "pi", "copilot", "cursor", "grok")
PACKAGE_IDS = {
    "browser",
    "dev-flow",
    "discovery",
    "git-flow",
    "infra-ops",
    "programming",
    "spec-flow",
}
ARCHIVE_NAMES = {f"cc-thingz-{target}.tar.gz" for target in TARGETS if target != "pi"}
ARCHIVE_NAMES.add("cc-thingz-pi.tgz")
INSTALL_ROOTS = {
    "claude": ".claude-plugin/marketplace.json",
    "codex": ".agents/plugins/marketplace.json",
    "copilot": ".github/plugin/marketplace.json",
    "cursor": ".cursor-plugin/marketplace.json",
    "grok": ".claude-plugin/marketplace.json",
    "pi": "package.json",
}
PI_NATIVE_EXTENSION_ENTRIES = {
    "./extensions/ask-user-question.ts",
    "./extensions/hook-runner/index.ts",
    "./extensions/permission-gate.ts",
    "./extensions/plan-mode/index.ts",
    "./extensions/structured-output.ts",
    "./extensions/todo.ts",
}
PI_NATIVE_EXTENSION_FILES = {
    entry.removeprefix("./") for entry in PI_NATIVE_EXTENSION_ENTRIES
}
PI_NATIVE_ASSET_ROOT = REPO_ROOT / "src/plugins/pi/extensions"


def _pi_native_asset_files() -> set[str]:
    return {
        str(path.relative_to(PI_NATIVE_ASSET_ROOT))
        for path in PI_NATIVE_ASSET_ROOT.rglob("*")
        if path.is_file()
        and ".agentbundler" not in path.parts
        and "__pycache__" not in path.parts
        and path.suffix != ".pyc"
    }


EXPECTED_AGENTS = {
    "claude": {"engineer", "reviewer", "runner"},
    "codex": {"advisor", "reviewer", "runner"},
    "pi": {"advisor", "engineer", "reviewer", "runner"},
    "copilot": {"reviewer", "runner"},
    "cursor": {"reviewer", "runner"},
    "grok": {"engineer", "reviewer", "runner"},
}


def _run_package(output: Path) -> None:
    subprocess.run(
        ["agbun", "package", "--root", str(REPO_ROOT), "--out", str(output)],
        check=True,
    )


@pytest.fixture(scope="module")
def release_artifacts(tmp_path_factory: pytest.TempPathFactory) -> Path:
    output = tmp_path_factory.mktemp("release-artifacts")
    _run_package(output)
    return output


def _archive_target(path: Path) -> str:
    return (
        path.name.removeprefix("cc-thingz-")
        .removesuffix(".tar.gz")
        .removesuffix(".tgz")
    )


def _archive_members(path: Path) -> set[str]:
    with tarfile.open(path, "r:gz") as archive:
        return {member.name for member in archive.getmembers()}


def _agent_names(target: str) -> set[str]:
    if target == "pi":
        paths = (REPO_ROOT / "dist/pi/agents").glob("*.md")
    elif target == "codex":
        paths = (REPO_ROOT / "dist/codex/.codex/agents").glob("*.toml")
    else:
        paths = (
            path
            for path in (REPO_ROOT / "dist" / target).rglob("*")
            if path.is_file() and "agents" in path.parts
        )
    return {path.stem.removesuffix(".agent") for path in paths}


def _skill_names(target: str) -> set[str]:
    return {
        path.parent.name
        for path in (REPO_ROOT / "dist" / target).rglob("SKILL.md")
        if "node_modules" not in path.parts
    }


def _metadata(path: str) -> dict[str, object]:
    return frontmatter.loads((REPO_ROOT / path).read_text()).metadata


def _codex_agent(name: str) -> dict[str, object]:
    return tomllib.loads(
        (REPO_ROOT / "dist/codex/.codex/agents" / f"{name}.toml").read_text()
    )


def test_release_archives_have_native_install_roots(release_artifacts: Path) -> None:
    archives = {path.name: path for path in release_artifacts.iterdir()}
    assert set(archives) == ARCHIVE_NAMES

    for archive_path in archives.values():
        target = _archive_target(archive_path)
        members = _archive_members(archive_path)
        assert INSTALL_ROOTS[target] in members
        assert all(not name.startswith(("/", "../")) for name in members)
        assert all("/__pycache__/" not in f"/{name}" for name in members)
        assert all(not name.endswith(".pyc") for name in members)
        if target != "pi":
            archive_packages = {
                name.split("/", 1)[0] for name in members if "/" in name
            }
            assert PACKAGE_IDS <= archive_packages

    codex_members = _archive_members(archives["cc-thingz-codex.tar.gz"])
    assert {
        ".codex/agents/advisor.toml",
        ".codex/agents/reviewer.toml",
        ".codex/agents/runner.toml",
    } <= codex_members

    pi_members = _archive_members(archives["cc-thingz-pi.tgz"])
    assert "extensions/agentbundler-hooks.ts" in pi_members
    assert PI_NATIVE_EXTENSION_FILES <= pi_members
    assert _pi_native_asset_files() <= pi_members


def test_release_archives_are_deterministic(
    release_artifacts: Path, tmp_path: Path
) -> None:
    second = tmp_path / "second"
    _run_package(second)

    first_hashes = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in release_artifacts.iterdir()
    }
    second_hashes = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in second.iterdir()
    }
    assert first_hashes == second_hashes


@pytest.mark.parametrize(
    ("target", "command"),
    [
        ("claude", ("plugin", "marketplace", "add")),
        ("codex", ("plugin", "marketplace", "add")),
        ("copilot", ("plugin", "marketplace", "add")),
        ("grok", ("plugin", "marketplace", "add")),
    ],
)
def test_release_marketplace_registers_in_isolated_home(
    release_artifacts: Path,
    tmp_path: Path,
    target: str,
    command: tuple[str, ...],
) -> None:
    executable = shutil.which(target)
    if executable is None:
        pytest.skip(f"{target} CLI is not installed")

    archive_path = release_artifacts / f"cc-thingz-{target}.tar.gz"
    package_root = tmp_path / "package"
    package_root.mkdir()
    with tarfile.open(archive_path, "r:gz") as archive:
        archive.extractall(package_root, filter="data")

    environment = os.environ.copy()
    environment.update(
        {
            "HOME": str(tmp_path / "home"),
            "CLAUDE_CONFIG_DIR": str(tmp_path / "claude"),
            "CODEX_HOME": str(tmp_path / "codex"),
            "XDG_CACHE_HOME": str(tmp_path / "cache"),
            "XDG_CONFIG_HOME": str(tmp_path / "config"),
        }
    )
    for key in (
        "HOME",
        "CLAUDE_CONFIG_DIR",
        "CODEX_HOME",
        "XDG_CACHE_HOME",
        "XDG_CONFIG_HOME",
    ):
        Path(environment[key]).mkdir(parents=True, exist_ok=True)

    arguments = [executable, *command, str(package_root)]
    if target == "codex":
        arguments.append("--json")
    subprocess.run(arguments, env=environment, check=True)


def test_claude_release_hooks_load_once(
    release_artifacts: Path, tmp_path: Path
) -> None:
    claude = shutil.which("claude")
    if claude is None:
        pytest.skip("Claude CLI is not installed")

    package_root = tmp_path / "package"
    package_root.mkdir()
    with tarfile.open(release_artifacts / "cc-thingz-claude.tar.gz", "r:gz") as archive:
        archive.extractall(package_root, filter="data")

    for package_id in ("dev-flow", "git-flow"):
        manifest = json.loads(
            (package_root / package_id / ".claude-plugin/plugin.json").read_text()
        )
        assert "hooks" not in manifest
        assert (package_root / package_id / "hooks/hooks.json").is_file()

    environment = os.environ.copy()
    environment.update(
        {
            "HOME": str(tmp_path / "home"),
            "CLAUDE_CONFIG_DIR": str(tmp_path / "claude"),
            "XDG_CACHE_HOME": str(tmp_path / "cache"),
            "XDG_CONFIG_HOME": str(tmp_path / "config"),
        }
    )
    for key in (
        "HOME",
        "CLAUDE_CONFIG_DIR",
        "XDG_CACHE_HOME",
        "XDG_CONFIG_HOME",
    ):
        Path(environment[key]).mkdir(parents=True, exist_ok=True)

    project = tmp_path / "project"
    project.mkdir()
    subprocess.run(
        [claude, "plugin", "marketplace", "add", str(package_root)],
        cwd=project,
        env=environment,
        check=True,
    )
    for package_id in ("dev-flow", "git-flow"):
        subprocess.run(
            [
                claude,
                "plugin",
                "install",
                f"{package_id}@cc-thingz",
                "--scope",
                "user",
            ],
            cwd=project,
            env=environment,
            check=True,
        )

    plugins = json.loads(
        subprocess.run(
            [claude, "plugin", "list", "--json"],
            cwd=project,
            env=environment,
            capture_output=True,
            check=True,
            text=True,
        ).stdout
    )
    by_id = {plugin["id"].split("@", 1)[0]: plugin for plugin in plugins}
    for package_id in ("dev-flow", "git-flow"):
        assert by_id[package_id].get("errors", []) == []


def test_pi_release_archive_installs_in_isolated_project(
    release_artifacts: Path, tmp_path: Path
) -> None:
    pi = shutil.which("pi")
    if pi is None:
        pytest.skip("Pi CLI is not installed")
    assert pi is not None

    project = tmp_path / "project"
    project.mkdir()
    environment = os.environ.copy()
    environment.update(
        {
            "HOME": str(tmp_path / "home"),
            "PI_CODING_AGENT_DIR": str(tmp_path / "agent"),
            "XDG_CACHE_HOME": str(tmp_path / "cache"),
            "XDG_CONFIG_HOME": str(tmp_path / "config"),
            "PI_OFFLINE": "1",
        }
    )
    archive = release_artifacts / "cc-thingz-pi.tgz"
    subprocess.run(
        [pi, "install", str(archive), "-l", "--approve"],
        cwd=project,
        env=environment,
        check=True,
    )

    settings = json.loads((project / ".pi/settings.json").read_text())
    assert any(package.endswith("cc-thingz-pi.tgz") for package in settings["packages"])


def test_generated_target_inventory_matches_supported_contract() -> None:
    source_skills = {
        path.parent.name for path in (REPO_ROOT / "src/skills").glob("*/SKILL.md")
    }
    assert len(source_skills) == 29

    for target in TARGETS:
        assert _agent_names(target) == EXPECTED_AGENTS[target]
        expected_skills = source_skills - (
            {"deploying-infra"} if target != "claude" else set()
        )
        assert _skill_names(target) == expected_skills

    generated_extensions = {
        f"extensions/{path.name}"
        for path in (REPO_ROOT / "dist/pi/extensions").glob("*.ts")
    }
    assert generated_extensions == {
        "extensions/agentbundler-hooks.ts",
        "extensions/ask-user-question.ts",
        "extensions/permission-gate.ts",
        "extensions/structured-output.ts",
        "extensions/todo.ts",
    }

    pi_manifest = json.loads((REPO_ROOT / "dist/pi/package.json").read_text())
    assert PI_NATIVE_EXTENSION_ENTRIES <= set(pi_manifest["pi"]["extensions"])
    compatibility = json.loads(
        (REPO_ROOT / "dist/pi/extensions/hooks.json").read_text()
    )
    assert set(compatibility["hooks"]) == {
        "Notification",
        "PreToolUse",
        "SessionEnd",
        "SessionStart",
        "Stop",
    }


def test_generated_agent_frontmatter_preserves_target_envelopes() -> None:
    source_description = _metadata("src/agents/reviewer.md")["description"]
    assert isinstance(source_description, str)
    assert _metadata("dist/claude/dev-flow/agents/reviewer.md") == {
        "color": "cyan",
        "description": source_description,
        "model": "sonnet",
        "name": "reviewer",
        "tools": ["Read", "Grep", "Glob", "LS"],
    }
    assert _metadata("dist/claude/discovery/agents/runner.md")["model"] == "haiku"
    assert _metadata("dist/claude/discovery/agents/runner.md")["tools"] == [
        "Read",
        "Grep",
        "Glob",
        "LS",
        "Bash(git status*)",
        "Bash(git log*)",
        "Bash(git show*)",
        "Bash(git diff*)",
        "Bash(ls*)",
        "Bash(wc*)",
        "Bash(head*)",
        "Bash(tail*)",
        "Bash(find*)",
        "Bash(du*)",
        "Bash(df*)",
        "Bash(ps*)",
    ]
    engineer_tools = _metadata("dist/claude/dev-flow/agents/engineer.md")["tools"]
    assert isinstance(engineer_tools, list)
    assert engineer_tools[:7] == [
        "Read",
        "Edit",
        "Write",
        "Bash",
        "Grep",
        "Glob",
        "LS",
    ]

    pi_expected = {
        "advisor": ("read, grep, find, ls, bash", False),
        "engineer": ("read, edit, write, bash, grep, find, ls", None),
        "reviewer": ("read, grep, find, ls", None),
        "runner": ("read, grep, find, ls, bash", False),
    }
    for role, (tools, completion_guard) in pi_expected.items():
        metadata = _metadata(f"dist/pi/agents/{role}.md")
        assert metadata["package"] == "cc-thingz"
        assert metadata["tools"] == tools
        assert metadata.get("completionGuard") is completion_guard

    for role in ("advisor", "reviewer", "runner"):
        profile = _codex_agent(role)
        assert profile["name"] == role
        assert (
            profile["description"] == _metadata(f"src/agents/{role}.md")["description"]
        )
        assert profile["sandbox_mode"] == "read-only"
        assert profile["developer_instructions"]


def test_public_metadata_matches_current_target_coverage() -> None:
    description = (
        "Portable skills, agents, hooks, and Pi extensions for Claude Code, "
        "Codex CLI, Copilot, Cursor, Grok, and Pi."
    )
    package = json.loads((REPO_ROOT / "package.json").read_text())
    project = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())
    bundle = json.loads((REPO_ROOT / "agentbundle.json").read_text())
    readme = (REPO_ROOT / "README.md").read_text()

    assert package["description"] == description
    assert project["project"]["name"] == "cc-thingz"
    assert project["project"]["description"] == (
        "Portable skills, agents, hooks, and Pi extensions for coding agents."
    )
    assert bundle["distribution"]["description"] == (
        "Portable skills, agents, hooks, and Pi-native extensions for coding agents."
    )
    assert "Gemini is retired." in readme
    assert "targets-6" in readme


def test_source_and_generated_versions_are_consistent() -> None:
    bundle = json.loads((REPO_ROOT / "agentbundle.json").read_text())
    expected = bundle["distribution"]["version"]
    pi_output = next(
        output for output in bundle["composition"] if output["target"] == "pi"
    )
    versions: dict[str, str] = {
        "agentbundle.pi": pi_output["aggregate"]["metadata"]["version"],
        "package.json": json.loads((REPO_ROOT / "package.json").read_text())["version"],
        "pyproject.toml": tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())[
            "project"
        ]["version"],
        "playwright package": json.loads(
            (REPO_ROOT / "src/skills/playwright-skill/scripts/package.json").read_text()
        )["version"],
        "dist/pi/package.json": json.loads(
            (REPO_ROOT / "dist/pi/package.json").read_text()
        )["version"],
    }
    uv_lock = tomllib.loads((REPO_ROOT / "uv.lock").read_text())
    versions["uv.lock"] = next(
        package["version"]
        for package in uv_lock["package"]
        if package["name"] == "cc-thingz"
    )

    for path in sorted((REPO_ROOT / "src/.agentbundler/packages").glob("*.json")):
        versions[str(path.relative_to(REPO_ROOT))] = json.loads(path.read_text())[
            "metadata"
        ]["version"]
    for target in ("claude", "grok"):
        catalog = json.loads(
            (REPO_ROOT / f"dist/{target}/.claude-plugin/marketplace.json").read_text()
        )
        versions[f"dist/{target} catalog"] = catalog["version"]
        versions.update(
            {
                f"dist/{target}/{plugin['name']} catalog": plugin["version"]
                for plugin in catalog["plugins"]
            }
        )
        for plugin_path in sorted(
            (REPO_ROOT / f"dist/{target}").glob("*/.claude-plugin/plugin.json")
        ):
            versions[str(plugin_path.relative_to(REPO_ROOT))] = json.loads(
                plugin_path.read_text()
            )["version"]
    for target, path in {
        "copilot": "dist/copilot/.github/plugin/marketplace.json",
        "cursor": "dist/cursor/.cursor-plugin/marketplace.json",
    }.items():
        catalog = json.loads((REPO_ROOT / path).read_text())
        versions[f"dist/{target} catalog"] = catalog["metadata"]["version"]
        versions.update(
            {
                f"dist/{target}/{plugin['name']} catalog": plugin["version"]
                for plugin in catalog["plugins"]
            }
        )
        pattern = (
            "*/plugin.json" if target == "copilot" else "*/.cursor-plugin/plugin.json"
        )
        for plugin_path in sorted((REPO_ROOT / f"dist/{target}").glob(pattern)):
            versions[str(plugin_path.relative_to(REPO_ROOT))] = json.loads(
                plugin_path.read_text()
            )["version"]
    for path in sorted((REPO_ROOT / "dist/codex").glob("*/.codex-plugin/plugin.json")):
        versions[str(path.relative_to(REPO_ROOT))] = json.loads(path.read_text())[
            "version"
        ]

    assert set(versions.values()) == {expected}, versions


def test_ci_typescript_filter_covers_native_pi_extension_sources() -> None:
    workflow = (REPO_ROOT / ".github/workflows/ci.yml").read_text()
    assert "- 'src/plugins/**/*.ts'" in workflow
    assert "- 'tests/pi-extensions/**/*.ts'" in workflow
    assert "src/pi-extensions/**/*.ts" not in workflow


def test_make_check_is_non_mutating_and_release_packages_artifacts() -> None:
    makefile = (REPO_ROOT / "Makefile").read_text()
    ci_workflow = (REPO_ROOT / ".github/workflows/ci.yml").read_text()
    release_workflow = (REPO_ROOT / ".github/workflows/release.yml").read_text()

    assert re.search(r"^check: check-agbun\b", makefile, re.MULTILINE)
    assert not re.search(r"^check: build\b", makefile, re.MULTILINE)
    dry_run = subprocess.run(
        ["make", "--no-print-directory", "-n", "check"],
        cwd=REPO_ROOT,
        capture_output=True,
        check=True,
        text=True,
    ).stdout
    assert "agbun check --root ." in dry_run
    assert "agbun build" not in dry_run

    generated_dry_run = subprocess.run(
        ["make", "--no-print-directory", "-n", "check-generated"],
        cwd=REPO_ROOT,
        capture_output=True,
        check=True,
        text=True,
    ).stdout
    assert "agbun build --root ." in generated_dry_run
    assert "git diff --exit-code -- dist" in generated_dry_run
    assert "agbun check --root ." in generated_dry_run
    validation_job = ci_workflow[
        ci_workflow.index("  validate:") : ci_workflow.index("  test:")
    ]
    test_job = ci_workflow[
        ci_workflow.index("  test:") : ci_workflow.index("  test-typescript:")
    ]
    for job in (validation_job, test_job):
        assert "- uses: oven-sh/setup-bun@v2" in job
        assert "- run: bun install --frozen-lockfile" in job
    assert "- run: make validate check-generated" in validation_job

    assert "- name: Build target-native distributions" in release_workflow
    assert "run: agbun build --root ." in release_workflow
    assert (
        'agbun package --root . --out "$RUNNER_TEMP/release-artifacts"'
        in release_workflow
    )
    assert "files: ${{ runner.temp }}/release-artifacts/*" in release_workflow
    assert '            --tag "${{ github.ref_name }}"' in release_workflow
    assert '            --repository "${{ github.repository }}"' in release_workflow
    assert "            --version" not in release_workflow
    assert "previous_tag=" not in release_workflow
    assert release_workflow.count("- run: uv sync --all-groups --extra test") == 2
    assert "sudo apt-get install --yes shellcheck" in release_workflow
    assert "go install mvdan.cc/sh/v3/cmd/shfmt@v3.13.1" in release_workflow
    project = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())
    assert any(
        dependency.startswith("ruff")
        for dependency in project["dependency-groups"]["dev"]
    )
    assert "- uses: oven-sh/setup-bun@v2" in release_workflow
    assert "- run: bun install --frozen-lockfile" in release_workflow
    node_package = json.loads((REPO_ROOT / "package.json").read_text())
    assert "markdownlint-cli2" in node_package["devDependencies"]
    assert "bunx --no-install markdownlint-cli2" in makefile
    for workflow in (ci_workflow, release_workflow):
        assert "AGBUN_VERSION" not in workflow
        assert "agentbundler/cmd/agbun@latest" in workflow


def test_release_tag_updates_agentbundle_versions(tmp_path: Path) -> None:
    source_script = REPO_ROOT / "scripts/release/release-tag"
    script = tmp_path / "scripts/release/release-tag"
    script.parent.mkdir(parents=True)
    shutil.copy2(source_script, script)

    files = {
        "agentbundle.json": {
            "version": 1,
            "distribution": {"version": "1.0.0"},
            "composition": [{"aggregate": {"metadata": {"version": "1.0.0"}}}],
        },
        "package.json": {"version": "1.0.0"},
        "src/skills/playwright-skill/scripts/package.json": {"version": "1.0.0"},
        "src/.agentbundler/packages/test.json": {
            "id": "test",
            "metadata": {"version": "1.0.0"},
        },
    }
    for relative, content in files.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(content, indent=2) + "\n")
    (tmp_path / "pyproject.toml").write_text(
        "[project]\n"
        'name = "test-release"\n'
        'version = "1.0.0"\n'
        'requires-python = ">=3.12"\n'
    )
    (tmp_path / "uv.lock").write_text('version = "1.0.0"\n')
    (tmp_path / "CHANGELOG.md").write_text("## [Unreleased]\n")
    compatibility_state = tmp_path / ".agentbundler/compatibility.json"
    compatibility_state.parent.mkdir()
    compatibility_state.write_text(
        json.dumps(
            {
                "version": 1,
                "files": [".claude-plugin/marketplace.json"],
                "pi": {"legacyPeerDeps": True},
            }
        )
        + "\n"
    )
    root_marketplace = tmp_path / ".claude-plugin/marketplace.json"
    root_marketplace.parent.mkdir()
    root_marketplace.write_text("before\n")
    (tmp_path / ".npmrc").write_text("legacy-peer-deps=true\n")
    uv = tmp_path / "bin/uv"
    uv.parent.mkdir()
    uv.write_text(
        """#!/usr/bin/env python3
from pathlib import Path
project = Path("pyproject.toml").read_text()
version = project.split('version = "', 1)[1].split('"', 1)[0]
Path("uv.lock").write_text(f'version = "{version}"\\n')
"""
    )
    uv.chmod(0o755)
    (tmp_path / "Makefile").write_text(
        "build:\n"
        "\t@mkdir -p dist .claude-plugin; "
        "echo generated > dist/build.txt; "
        "echo generated > .claude-plugin/marketplace.json\n"
    )

    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=tmp_path,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True
    )
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "initial"], cwd=tmp_path, check=True)
    environment = os.environ | {"PATH": f"{uv.parent}:{os.environ['PATH']}"}
    subprocess.run(
        ["bash", str(script), "v1.2.3"],
        cwd=tmp_path,
        check=True,
        env=environment,
    )

    bundle = json.loads((tmp_path / "agentbundle.json").read_text())
    assert bundle["distribution"]["version"] == "1.2.3"
    assert bundle["composition"][0]["aggregate"]["metadata"]["version"] == "1.2.3"
    assert (tmp_path / "uv.lock").read_text() == 'version = "1.2.3"\n'
    committed = subprocess.run(
        ["git", "show", "--format=", "--name-only", "HEAD"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
        text=True,
    ).stdout.splitlines()
    assert ".claude-plugin/marketplace.json" in committed
