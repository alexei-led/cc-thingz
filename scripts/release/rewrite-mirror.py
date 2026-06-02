#!/usr/bin/env python3
"""Rewrite plugin manifests for private mirror repos.

Usage: python scripts/release/rewrite-mirror.py <owner>/<repo>

Runs in CI on mirror repos (condition-gated in workflow). Safe to run
on the source repo — exits immediately when repo matches SOURCE_REPO.

Operates on the YAML source of truth (`src/plugins/marketplace.yaml`
and `src/plugins/*/plugin.yaml`) then runs `make build` to regenerate
the root manifests and dist/ tree.
"""

from __future__ import annotations

import glob
import os
import subprocess
import sys

import yaml

SOURCE_REPO = "alexei-led/cc-thingz"
SOURCE_URL = f"https://github.com/{SOURCE_REPO}"

# Per-mirror plugin rename maps: dir-name → new plugin (marketplace) name
MIRROR_NAMES: dict[str, dict[str, str]] = {
    "cc-forge": {
        "dev-flow": "review-lint-commit",
        "discovery": "cli-research-tools",
        "spec-flow": "spec-driven-planning",
        "infra-ops": "k8s-terraform-ops",
    },
}


def _dump_yaml(path: str, data: dict) -> None:
    with open(path, "w") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)


def main() -> None:
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <owner>/<repo>", file=sys.stderr)
        sys.exit(1)

    repo = sys.argv[1]
    if repo == SOURCE_REPO:
        print("Source repo — nothing to rewrite.")
        return

    repo_name = repo.split("/")[-1]
    mirror_url = f"https://github.com/{repo}"
    name_map = MIRROR_NAMES.get(repo_name, {})

    # Top-level marketplace metadata
    mp_yaml = "src/plugins/marketplace.yaml"
    if os.path.isfile(mp_yaml):
        with open(mp_yaml) as f:
            data = yaml.safe_load(f) or {}
        data["homepage"] = mirror_url
        data["repository"] = mirror_url
        _dump_yaml(mp_yaml, data)
        print(f"  {mp_yaml}")

    # Per-plugin renames + repo URL stamping
    for path in sorted(glob.glob("src/plugins/*/plugin.yaml")):
        plugin_dir = os.path.basename(os.path.dirname(path))
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        changed = False
        if plugin_dir in name_map:
            # Use marketplace_name so the source dir keeps its canonical name
            # but the generated marketplace entry shows the mirror-specific one.
            data["marketplace_name"] = name_map[plugin_dir]
            changed = True
        # Per-plugin homepage/repository are optional in plugin.yaml; only
        # rewrite when present (to mirror prior behaviour).
        if "repository" in data:
            data["repository"] = mirror_url
            changed = True
        if "homepage" in data and isinstance(data["homepage"], str):
            data["homepage"] = data["homepage"].replace(SOURCE_URL, mirror_url)
            changed = True
        if changed:
            _dump_yaml(path, data)
            print(f"  {path}")

    # Regenerate dist/ + root manifests from the rewritten YAML sources
    subprocess.run(["make", "build"], check=True)

    print(f"✓ Rewrote manifests for {repo}")


if __name__ == "__main__":
    main()
