"""Distribution and release contracts for Agent Bundler output."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
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
ARCHIVE_NAMES = {
    f"alexei-led-cc-thingz-{target}.tar.gz" for target in TARGETS if target != "pi"
}
ARCHIVE_NAMES.add("alexei-led-cc-thingz-pi.tgz")
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
        path.name.removeprefix("alexei-led-cc-thingz-")
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
        assert any(name.endswith("skills/releasing-code/SKILL.md") for name in members)
        assert any(
            name.endswith("skills/releasing-code/scripts/release_notes.py")
            for name in members
        )
        assert any(name.endswith("release-guard/hook.py") for name in members)
        if target != "pi":
            archive_packages = {
                name.split("/", 1)[0] for name in members if "/" in name
            }
            assert PACKAGE_IDS <= archive_packages

    codex_members = _archive_members(archives["alexei-led-cc-thingz-codex.tar.gz"])
    assert {
        ".codex/agents/advisor.toml",
        ".codex/agents/reviewer.toml",
        ".codex/agents/runner.toml",
    } <= codex_members

    pi_members = _archive_members(archives["alexei-led-cc-thingz-pi.tgz"])
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

    archive_path = release_artifacts / f"alexei-led-cc-thingz-{target}.tar.gz"
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
    with tarfile.open(
        release_artifacts / "alexei-led-cc-thingz-claude.tar.gz", "r:gz"
    ) as archive:
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
                f"{package_id}@alexei-led-cc-thingz",
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
    archive = release_artifacts / "alexei-led-cc-thingz-pi.tgz"
    subprocess.run(
        [pi, "install", str(archive), "-l", "--approve"],
        cwd=project,
        env=environment,
        check=True,
    )

    settings = json.loads((project / ".pi/settings.json").read_text())
    assert any(
        package.endswith("alexei-led-cc-thingz-pi.tgz")
        for package in settings["packages"]
    )


def test_generated_target_inventory_matches_supported_contract() -> None:
    source_skills = {
        path.parent.name for path in (REPO_ROOT / "src/skills").glob("*/SKILL.md")
    }
    assert len(source_skills) == 31
    assert f"skills-{len(source_skills)}-green" in (REPO_ROOT / "README.md").read_text()

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
        "reviewer": ("read, grep, find, ls, contact_supervisor", None),
        "runner": ("read, grep, find, ls, bash", False),
    }
    for role, (tools, completion_guard) in pi_expected.items():
        metadata = _metadata(f"dist/pi/agents/{role}.md")
        assert metadata["package"] == "cc-thingz"
        assert metadata["tools"] == tools
        assert metadata.get("completionGuard") is completion_guard

    reviewer_metadata = _metadata("dist/pi/agents/reviewer.md")
    assert reviewer_metadata["inheritProjectContext"] is True
    assert reviewer_metadata["skills"] == (
        "reviewing-code, improving-tests, documenting-code, spec-flow"
    )

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
    assert "format('{0}/release-artifacts/*', runner.temp)" in release_workflow
    assert '            --tag "$RELEASE_TAG"' in release_workflow
    assert '            --repository "$GITHUB_REPOSITORY"' in release_workflow
    assert "          name: ${{ inputs.tag || github.ref_name }}" in release_workflow
    assert "workflow_dispatch:" in release_workflow
    assert "notes_source_sha:" in release_workflow
    assert "Validate release version contract and notes" in release_workflow
    assert "Preserve existing release title and notes" in release_workflow
    assert "Refuse automatic resume of an existing release" in release_workflow
    assert "Verify repaired release title, notes, and assets" in release_workflow
    assert "overwrite_files: false" in release_workflow
    assert "generate_release_notes: false" in release_workflow
    assert (
        release_workflow.count(
            "softprops/action-gh-release@efb35369e0ad2afab669f228072c1b0d510eae64 # v3"
        )
        == 1
    )
    assert "gh release create" not in release_workflow
    assert "gh release edit" not in release_workflow
    assert '--expected-asset "alexei-led-cc-thingz-pi.tgz"' in release_workflow
    assert release_workflow.count("--expected-asset") == 12
    assert release_workflow.index("Generate release notes") < release_workflow.index(
        "softprops/action-gh-release@efb35369e0ad2afab669f228072c1b0d510eae64"
    )
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
    assert (
        "oven-sh/setup-bun@0c5077e51419868618aeaa5fe8019c62421857d6 # v2"
        in release_workflow
    )
    assert "no-cache: true" in release_workflow
    assert release_workflow.count("persist-credentials: false") == 4
    assert release_workflow.count("\n          cache: false\n") == 2
    assert release_workflow.count("enable-cache: false") == 2
    assert "run: bun install --frozen-lockfile" in release_workflow
    for revision in (
        "d23441a48e516b6c34aea4fa41551a30e30af803",
        "ece7cb06caefa5fff74198d8649806c4678c61a1",
        "924ae3a1cded613372ab5595356fb5720e22ba16",
        "37802adc94f370d6bfd71619e3f0bf239e1f3b78",
        "efb35369e0ad2afab669f228072c1b0d510eae64",
        "ea165f8d65b6e75b540449e92b4886f43607fa02",
    ):
        assert revision in release_workflow
    node_package = json.loads((REPO_ROOT / "package.json").read_text())
    assert "markdownlint-cli2" in node_package["devDependencies"]
    assert "bunx --no-install markdownlint-cli2" in makefile
    for workflow in (ci_workflow, release_workflow):
        assert "scripts/setup/install-agbun.sh" in workflow
        assert "agentbundler/cmd/agbun@latest" not in workflow


def test_release_workflow_repair_uses_selected_source_and_preserves_prior_notes() -> (
    None
):
    workflow = (REPO_ROOT / ".github/workflows/release.yml").read_text()
    assert "notes_source_sha:" in workflow
    assert "github.ref_name == github.event.repository.default_branch" in workflow
    assert "ref: ${{ inputs.tag || github.ref }}" not in workflow
    assert "ref: ${{ inputs.notes_source_sha }}" in workflow
    assert "path: notes-source" in workflow
    assert "sparse-checkout: CHANGELOG.md" in workflow
    assert "ref: ${{ inputs.tag }}" in workflow
    assert "path: release-target" in workflow
    assert "release_notes.py check-release" in workflow
    assert '--root "$RELEASE_ROOT"' in workflow
    assert '--changelog "$NOTES_CHANGELOG"' in workflow
    assert "notes-source/CHANGELOG.md" in workflow
    assert "release-target/src/.agentbundler/packages" in workflow
    version_check = workflow.index("Validate release version contract and notes")
    build = workflow.index("Build target-native distributions")
    generated_check = workflow.index("Check generated release manifests")
    package = workflow.index("Package target-native distributions")
    assert version_check < build < generated_check < package

    backup_start = workflow.index("Preserve existing release title and notes")
    backup_end = workflow.index("Upload release repair backup")
    preflight = workflow[backup_start:backup_end]
    assert "--json tagName,name,body,isDraft,isPrerelease,assets" in preflight
    assert "check-release-identity" in preflight
    assert "--title" not in preflight
    assert (
        "release-notes-backup-${{ inputs.tag }}-"
        "${{ github.run_id }}-${{ github.run_attempt }}" in workflow
    )
    assert "retention-days: 90" in workflow
    assert "overwrite: false" in workflow
    assert "steps.release-backup-artifact.outputs.artifact-url" in workflow
    assert workflow.index("Upload release repair backup") < workflow.index(
        "softprops/action-gh-release@efb35369e0ad2afab669f228072c1b0d510eae64"
    )
    action = workflow.index(
        "softprops/action-gh-release@efb35369e0ad2afab669f228072c1b0d510eae64"
    )
    verification = workflow.index("Verify repaired release title, notes, and assets")
    assert action < verification
    postflight = workflow[verification:]
    assert "--json tagName,name,body,isDraft,isPrerelease,assets" in postflight
    assert "check-release-identity" in postflight
    assert '--title "$RELEASE_TAG"' in postflight
    assert "actual != expected" in postflight


def test_release_tag_prepare_and_finalize_require_reviewed_commit(
    tmp_path: Path,
) -> None:
    source_script = REPO_ROOT / "scripts/release/release-tag"
    script = tmp_path / "scripts/release/release-tag"
    script.parent.mkdir(parents=True)
    shutil.copy2(source_script, script)
    checker_source = REPO_ROOT / "src/skills/releasing-code/scripts/release_notes.py"
    checker = tmp_path / "src/skills/releasing-code/scripts/release_notes.py"
    checker.parent.mkdir(parents=True)
    shutil.copy2(checker_source, checker)

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
    (tmp_path / "uv.lock").write_text(
        'version = 1\nrevision = 3\nrequires-python = ">=3.12"\n\n'
        '[[package]]\nname = "test-release"\nversion = "1.0.0"\n'
        'source = { virtual = "." }\n'
    )
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
import tomllib
version = tomllib.loads(Path("pyproject.toml").read_text())["project"]["version"]
Path("uv.lock").write_text(
    'version = 1\\nrevision = 3\\nrequires-python = ">=3.12"\\n\\n'
    '[[package]]\\nname = "test-release"\\nversion = "' + version + '"\\n'
    'source = { virtual = "." }\\n'
)
"""
    )
    uv.chmod(0o755)
    (tmp_path / "Makefile").write_text(
        "build:\n"
        "\t@mkdir -p dist .claude-plugin; "
        "echo generated > dist/build.txt; "
        "echo generated > .claude-plugin/marketplace.json\n"
        "ci:\n"
        "\t@echo fixture ci passed\n"
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
    initial_head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
        text=True,
    ).stdout.strip()
    environment = os.environ | {"PATH": f"{uv.parent}:{os.environ['PATH']}"}
    equal_version = subprocess.run(
        ["bash", str(script), "prepare", "v1.0.0"],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert equal_version.returncode != 0
    assert "must be greater than current project version" in equal_version.stderr
    assert 'version = "1.0.0"' in (tmp_path / "pyproject.toml").read_text()
    assert not subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
        text=True,
    ).stdout

    prepared = subprocess.run(
        ["bash", str(script), "prepare", "v1.2.3"],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        check=True,
    )

    bundle = json.loads((tmp_path / "agentbundle.json").read_text())
    assert bundle["distribution"]["version"] == "1.2.3"
    assert bundle["composition"][0]["aggregate"]["metadata"]["version"] == "1.2.3"
    assert 'version = "1.2.3"' in (tmp_path / "uv.lock").read_text()
    assert (
        subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=tmp_path,
            capture_output=True,
            check=True,
            text=True,
        ).stdout.strip()
        == initial_head
    )
    assert not subprocess.run(
        ["git", "tag", "--list", "v1.2.3"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
        text=True,
    ).stdout.strip()
    assert subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
        text=True,
    ).stdout.strip()
    assert (
        ".claude-plugin/marketplace.json"
        in subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=tmp_path,
            capture_output=True,
            check=True,
            text=True,
        ).stdout
    )
    assert "Review CHANGELOG.md" in prepared.stdout

    changelog = tmp_path / "CHANGELOG.md"
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-qm", "release: v1.2.3"], cwd=tmp_path, check=True
    )
    placeholder_head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
        text=True,
    ).stdout.strip()
    rejected = subprocess.run(
        ["bash", str(script), "finalize", "v1.2.3"],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert rejected.returncode != 0
    assert "meaningful user-visible content" in rejected.stderr
    assert not subprocess.run(
        ["git", "tag", "--list", "v1.2.3"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
        text=True,
    ).stdout.strip()
    assert (
        subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=tmp_path,
            capture_output=True,
            check=True,
            text=True,
        ).stdout.strip()
        == placeholder_head
    )

    changelog.write_text(
        "## [Unreleased]\n\n"
        "## [1.2.3] - 2026-06-08\n\n"
        "- Adds deterministic release validation.\n"
    )
    subprocess.run(["git", "add", "CHANGELOG.md"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "--amend", "--no-edit"], cwd=tmp_path, check=True)
    release_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
        text=True,
    ).stdout.strip()

    finalized = subprocess.run(
        ["bash", str(script), "finalize", "v1.2.3"],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        check=True,
    )

    assert "fixture ci passed" in finalized.stdout
    assert (
        subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=tmp_path,
            capture_output=True,
            check=True,
            text=True,
        ).stdout.strip()
        == release_commit
    )
    assert (
        subprocess.run(
            ["git", "rev-parse", "refs/tags/v1.2.3^{}"],
            cwd=tmp_path,
            capture_output=True,
            check=True,
            text=True,
        ).stdout.strip()
        == release_commit
    )
    assert not subprocess.run(
        ["git", "remote"], cwd=tmp_path, capture_output=True, check=True, text=True
    ).stdout.strip()

    remote = tmp_path.parent / f"{tmp_path.name}-origin.git"
    subprocess.run(["git", "init", "--bare", "-q", str(remote)], check=True)
    subprocess.run(
        ["git", "remote", "add", "origin", str(remote)], cwd=tmp_path, check=True
    )
    subprocess.run(
        ["git", "push", "origin", "refs/tags/v1.2.3"], cwd=tmp_path, check=True
    )
    subprocess.run(["git", "tag", "-d", "v1.2.3"], cwd=tmp_path, check=True)
    remote_before = subprocess.run(
        ["git", "ls-remote", "--refs", "origin", "refs/tags/v1.2.3"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
        text=True,
    ).stdout
    refused = subprocess.run(
        ["bash", str(script), "prepare", "v1.2.3"],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    remote_after = subprocess.run(
        ["git", "ls-remote", "--refs", "origin", "refs/tags/v1.2.3"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
        text=True,
    ).stdout
    assert refused.returncode != 0
    assert "already exists on remote 'origin'" in refused.stderr
    assert remote_after == remote_before
    assert (
        subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=tmp_path,
            capture_output=True,
            check=True,
            text=True,
        ).stdout
        == ""
    )


@pytest.mark.parametrize("target", TARGETS)
def test_release_doctor_runs_without_checkout(
    release_artifacts: Path, tmp_path: Path, target: str
) -> None:
    suffix = "pi.tgz" if target == "pi" else f"{target}.tar.gz"
    archive_path = release_artifacts / f"alexei-led-cc-thingz-{suffix}"
    package = tmp_path / "installed"
    package.mkdir()
    with tarfile.open(archive_path, "r:gz") as archive:
        archive.extractall(package, filter="data")
    owner = package if target == "pi" else package / "discovery"
    skill = owner / "skills" / "installation-doctor"
    script = skill / "scripts" / "doctor.py"
    assert (skill / "SKILL.md").is_file()
    empty = tmp_path / "empty"
    empty.mkdir()
    environment = {**os.environ, "PYTHONPATH": ""}
    scan_args = (
        ["--plugin-root", str(package)]
        if target in ("codex", "claude")
        else ["--skill-root", str(empty)]
    )
    result = subprocess.run(
        [sys.executable, "-B", str(script), *scan_args, "--json"],
        cwd=empty,
        env=environment,
        capture_output=True,
        text=True,
        timeout=15,
        check=True,
    )
    report = json.loads(result.stdout)
    assert set(report["canonical_packages"]) == PACKAGE_IDS
    assert "installation-doctor" in report["canonical_packages"]["discovery"]["skills"]
    assert not [item for item in report["checks"] if item["status"] == "failed"]
    assert not list(empty.iterdir())
    if target in ("codex", "claude"):
        assert {item["name"] for item in report["plugins"]} == PACKAGE_IDS
        versions = [
            item for item in report["checks"] if item["check"] == "package-version"
        ]
        assert len(versions) == len(PACKAGE_IDS)
        assert all(item["status"] == "passed" for item in versions)
