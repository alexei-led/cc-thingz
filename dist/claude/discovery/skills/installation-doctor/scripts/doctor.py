"""Inspect cc-thingz resources without executing hooks or modifying installations."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, TypedDict

Status = Literal["passed", "failed", "skipped", "unsupported"]


class CheckResult(TypedDict):
    check: str
    status: Status
    reason: str
    command: list[str] | None
    cwd: str
    scope: list[str]
    timestamp: str


OBSOLETE = {
    "dev-tools": ["discovery", "git-flow"],
    "dev-workflow": ["dev-flow"],
    "spec-dev": ["spec-flow"],
    "go-dev": ["programming"],
    "py-dev": ["programming"],
    "python-dev": ["programming"],
    "rust-dev": ["programming"],
    "ts-dev": ["programming"],
    "typescript-dev": ["programming"],
    "web-dev": ["programming"],
    "test-e2e": ["browser"],
    "browser-automation": ["browser"],
}
MANIFESTS = (".codex-plugin/plugin.json", ".claude-plugin/plugin.json")


class Inspection:
    def __init__(self, repo: Path | None) -> None:
        self.repo = repo
        self.results: list[CheckResult] = []

    def add(self, check: str, status: Status, reason: str, paths: list[Path]) -> None:
        self.results.append(
            {
                "check": check,
                "status": status,
                "reason": reason,
                "command": None,
                "cwd": str(self.repo or Path.cwd()),
                "scope": [str(path) for path in paths],
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )

    def read_json(self, path: Path) -> dict:
        try:
            if path.stat().st_size > 2_000_000:
                raise ValueError("oversized")
            value = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(value, dict):
                raise ValueError("expected object")
            return value
        except (OSError, UnicodeError, ValueError):
            self.add("metadata", "failed", "Unreadable or invalid JSON object", [path])
            return {}

    def canonical(self) -> dict[str, dict]:
        if self.repo is None:
            return self.bundled()
        catalog = {}
        manifests = sorted((self.repo / "src/.agentbundler/packages").glob("*.json"))
        if not manifests:
            self.add(
                "catalog", "failed", "No source package manifests found", [self.repo]
            )
        for path in manifests:
            data = self.read_json(path)
            assets = data.get("assets", [])
            if not isinstance(assets, list):
                self.add("catalog", "failed", "Invalid assets list", [path])
                continue
            skills = [
                item["path"].split("/")[1]
                for item in assets
                if isinstance(item, dict)
                and isinstance(item.get("path"), str)
                and item["path"].startswith("skills/")
                and len(item["path"].split("/")) == 2
                and item["path"].split("/")[1] not in (".", "..")
            ]
            metadata = data.get("metadata", {})
            catalog[path.stem] = {
                "skills": skills,
                "skill_targets": {
                    item["path"].split("/")[1]: item["targets"]
                    for item in assets
                    if isinstance(item, dict)
                    and item.get("path") in [f"skills/{skill}" for skill in skills]
                    and isinstance(item.get("targets"), list)
                },
                "version": metadata.get("version")
                if isinstance(metadata, dict)
                else None,
                "source": str(path),
                "resources": {
                    skill: ["SKILL.md"]
                    + [
                        str(helper.relative_to(self.repo / "src/skills" / skill))
                        for helper in sorted(
                            (self.repo / "src/skills" / skill / "scripts").rglob("*")
                        )
                        if helper.is_file() and "__pycache__" not in helper.parts
                    ]
                    + [
                        str(asset.relative_to(self.repo / "src/skills" / skill))
                        for asset in sorted(
                            (self.repo / "src/skills" / skill / "assets").rglob("*")
                        )
                        if asset.is_file()
                    ]
                    for skill in skills
                },
            }
        return catalog

    def bundled(self) -> dict[str, dict]:
        catalog_path = Path(__file__).resolve().parent.parent / "assets/catalog.json"
        catalog = self.read_json(catalog_path)
        version = None
        version_source = catalog_path
        for parent in Path(__file__).resolve().parents:
            for suffix in (
                *MANIFESTS,
                ".cursor-plugin/plugin.json",
                "plugin.json",
                "package.json",
            ):
                path = parent / suffix
                if not path.is_file():
                    continue
                metadata = self.read_json(path)
                if metadata.get("name") not in (
                    "discovery",
                    "@cc-thingz/discovery",
                    "cc-thingz",
                ):
                    continue
                candidate = metadata.get("version")
                if isinstance(candidate, str) and candidate:
                    version, version_source = candidate, path
                    break
            if version is not None:
                break
        self.add(
            "catalog-version",
            "passed" if version else "skipped",
            f"Bundled release baseline {version}"
            if version
            else "No release manifest; version comparison unavailable (use --repo)",
            [version_source],
        )
        for package in catalog.values():
            package["version"] = version
            package["source"] = str(catalog_path)
        return catalog

    def plugins(self, roots: list[Path]) -> list[dict]:
        found = {}
        for root in roots:
            if not root.is_dir():
                self.add("plugin-root", "skipped", "Directory not present", [root])
                continue
            for depth in range(4):
                for suffix in MANIFESTS:
                    for path in sorted(root.glob("*/" * depth + suffix)):
                        plugin = path.parent.parent.resolve()
                        if not plugin.is_relative_to(root.resolve()):
                            continue
                        if plugin in found:
                            continue
                        data = self.read_json(path)
                        name = data.get("name")
                        if not isinstance(name, str) or not name:
                            self.add(
                                "plugin-name", "failed", "Missing plugin name", [path]
                            )
                            continue
                        found[plugin] = {
                            "name": name,
                            "target": "codex"
                            if suffix.startswith(".codex")
                            else "claude",
                            "version": data.get("version"),
                            "source": str(plugin),
                        }
        return sorted(found.values(), key=lambda item: item["source"])

    def hooks(self, plugin: Path) -> None:
        path = plugin / "hooks/hooks.json"
        if not path.is_file():
            return
        events = self.read_json(path).get("hooks")
        if not isinstance(events, dict):
            self.add("hook-registrations", "unsupported", "Unknown hook schema", [path])
            return
        seen: set[str] = set()
        duplicates = 0
        for event, groups in events.items():
            if not isinstance(groups, list):
                self.add("hook-registrations", "failed", "Invalid event groups", [path])
                continue
            for group in groups:
                if not isinstance(group, dict) or not isinstance(
                    group.get("hooks"), list
                ):
                    self.add(
                        "hook-registrations", "failed", "Invalid hook group", [path]
                    )
                    continue
                for hook in group["hooks"]:
                    identity = json.dumps(
                        [event, {k: v for k, v in group.items() if k != "hooks"}, hook],
                        sort_keys=True,
                    )
                    digest = hashlib.sha256(identity.encode()).hexdigest()
                    duplicates += digest in seen
                    seen.add(digest)
        self.add(
            "hook-registrations",
            "failed" if duplicates else "passed",
            f"{duplicates} exact duplicate registrations within this manifest; "
            "runtime activation was not inspected",
            [path],
        )


def inspect(
    repo: Path | None,
    roots: list[Path],
    config_root: Path | None,
    skill_roots: list[Path] | None = None,
) -> dict:
    scan = Inspection(repo)
    catalog = scan.canonical()
    plugins = scan.plugins(roots)
    skills: dict[str, list[str]] = defaultdict(list)
    names: dict[str, list[str]] = defaultdict(list)
    for root in skill_roots or []:
        if not root.is_dir():
            scan.add("skill-root", "skipped", "Directory not present", [root])
        for path in sorted(root.glob("*/SKILL.md")):
            skills[path.parent.name].append(str(path))
    for plugin in plugins:
        name = plugin["name"]
        path = Path(plugin["source"])
        names[name].append(str(path))
        if name in OBSOLETE:
            scan.add(
                "obsolete-package",
                "failed",
                f"{name}: review migration to {', '.join(OBSOLETE[name])}",
                [path],
            )
        expected = catalog.get(name)
        if expected:
            scan.add(
                "package-version",
                (
                    "skipped"
                    if expected["version"] is None
                    else "passed"
                    if plugin["version"] == expected["version"]
                    else "failed"
                ),
                f"Installed {plugin['version']}; baseline {expected['version']}",
                [path],
            )
            for skill in expected["skills"]:
                targets = expected["skill_targets"].get(skill)
                if targets is not None and plugin["target"] not in targets:
                    continue
                skill_path = path / "skills" / skill
                required = [skill_path / item for item in expected["resources"][skill]]
                missing = [item for item in required if not item.is_file()]
                scan.add(
                    "skill-resources",
                    "failed" if missing else "passed",
                    f"{skill}: {len(missing)} missing skill/helper files",
                    missing or [skill_path],
                )
        for skill_file in sorted((path / "skills").glob("*/SKILL.md")):
            skills[skill_file.parent.name].append(str(skill_file))
        scan.hooks(path)
    for kind, inventory in (("plugin", names), ("skill", skills)):
        for name, sources in sorted(inventory.items()):
            if len(sources) > 1:
                scan.add(
                    f"duplicate-{kind}",
                    "failed",
                    f"{name}: {len(sources)} copies on disk; activation unknown",
                    [Path(source) for source in sources],
                )
    if config_root is not None:
        for role in ("advisor", "reviewer", "runner"):
            path = config_root / "agents" / f"{role}.toml"
            scan.add(
                "codex-agent-profile",
                "passed" if path.is_file() else "failed",
                f"{role}: profile {'present' if path.is_file() else 'missing'}; "
                "loading and effective permissions not verified",
                [path],
            )
    else:
        scan.add("codex-agent-profile", "skipped", "No --config-root supplied", [])
    scan.add(
        "runtime-support",
        "unsupported",
        "Static inventory cannot establish enabled plugins, hook event support, "
        "helper dependencies, or effective agent permissions",
        roots,
    )
    return {
        "schema_version": 1,
        "canonical_packages": catalog,
        "plugins": plugins,
        "skills": dict(sorted(skills.items())),
        "checks": scan.results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo",
        type=Path,
        help="Optional checkout for source comparison instead of bundled baseline",
    )
    parser.add_argument("--plugin-root", action="append", type=Path)
    parser.add_argument("--skill-root", action="append", type=Path)
    parser.add_argument("--config-root", type=Path, help="Codex .codex directory")
    parser.add_argument(
        "--json", action="store_true", help="Emit schema-versioned JSON"
    )
    args = parser.parse_args(argv)
    roots = (
        args.plugin_root
        if args.plugin_root is not None
        else []
        if args.skill_root is not None or args.config_root is not None
        else [
            Path.home() / ".codex/plugins/cache/alexei-led-cc-thingz",
        ]
    )
    skill_roots = args.skill_root or []
    if (
        args.plugin_root is None
        and args.skill_root is None
        and args.config_root is None
    ):
        skill_roots = [Path.home() / ".codex/skills", Path.home() / ".agents/skills"]
    report = inspect(
        args.repo.resolve() if args.repo is not None else None,
        [p.resolve() for p in roots],
        args.config_root.resolve() if args.config_root is not None else None,
        [p.resolve() for p in skill_roots],
    )
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("cc-thingz doctor: disk inventory (activation unknown)")
        for name, package in report["canonical_packages"].items():
            print(
                f"canonical {name}@{package['version']}: {', '.join(package['skills'])}"
            )
        for plugin in report["plugins"]:
            print(f"installed {plugin['name']}@{plugin['version']}: {plugin['source']}")
        for check in report["checks"]:
            print(f"{check['status']}: {check['check']}: {check['reason']}")
            for path in check["scope"]:
                print(f"  {path}")
    return int(any(item["status"] == "failed" for item in report["checks"]))


if __name__ == "__main__":
    raise SystemExit(main())
