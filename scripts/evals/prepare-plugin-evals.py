#!/usr/bin/env python3
"""Build an owned temporary `claude plugin eval` tree for one package.

Mirrors prepare-skill-evals.py's ownership/safety model, but for the
`claude plugin eval` harness: that CLI needs a whole plugin directory
(plugin.json, skills/, hooks/, ...) as its target, with cases injected at
`<target>/evals/<skill>/<case>/{prompt.md,graders/*.md}`. Fixtures never ship
inside `dist/`; this script copies the built plugin, then layers fixtures
from `tests/plugin-evals/<package>/<skill>/evals/` on top of the copy.
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = next(
    p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").is_file()
)
DIST_DIR = ROOT / "dist"
FIXTURES_DIR = ROOT / "tests" / "plugin-evals"
DEFAULT_OUT = Path("/tmp/cc-thingz-plugin-eval-root")
SOURCE_TARGET = "claude"
MARKER = ".cc-thingz-plugin-eval-owner.json"


class PluginEvalPrepError(Exception):
    """Plugin eval preparation failed."""


def read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise PluginEvalPrepError(f"cannot read {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise PluginEvalPrepError(f"expected JSON object: {path}")
    return data


def fixture_cases(skill_fixture_dir: Path) -> list[str]:
    evals_dir = skill_fixture_dir / "evals"
    cases = []
    for case_dir in sorted(p for p in evals_dir.iterdir() if p.is_dir()):
        # case.yaml carries its own `graders:` list; the prompt.md + graders/*.md
        # split needs an actual graders/ folder alongside it.
        if (case_dir / "case.yaml").is_file():
            cases.append(case_dir.name)
            continue
        has_prompt = (case_dir / "prompt.md").is_file()
        graders = sorted((case_dir / "graders").glob("*.md"))
        if not has_prompt or not graders:
            raise PluginEvalPrepError(f"invalid eval case: {case_dir}")
        cases.append(case_dir.name)
    if not cases:
        raise PluginEvalPrepError(f"no eval cases found: {evals_dir}")
    return cases


def inventory() -> dict:
    compiled = {
        f"{path.parents[2].name}/{path.parent.name}"
        for path in sorted((DIST_DIR / SOURCE_TARGET).glob("*/skills/*/SKILL.md"))
    }
    active = []
    for skill_fixture_dir in sorted(FIXTURES_DIR.glob("*/*")):
        if not (skill_fixture_dir / "evals").is_dir():
            continue
        identity = f"{skill_fixture_dir.parent.name}/{skill_fixture_dir.name}"
        if identity not in compiled:
            raise PluginEvalPrepError(
                f"fixture has no compiled {SOURCE_TARGET} skill: {identity}"
            )
        active.append({"skill": identity, "cases": fixture_cases(skill_fixture_dir)})
    packages = sorted({entry["skill"].split("/")[0] for entry in active})
    return {
        "source_target": SOURCE_TARGET,
        "active": active,
        "packages": packages,
        "skills": len(active),
        "cases": sum(len(entry["cases"]) for entry in active),
    }


def validate_output(out: Path) -> Path:
    if out.is_symlink():
        raise PluginEvalPrepError("output directory must not be a symlink")
    resolved = out.resolve()
    root = ROOT.resolve()
    if resolved == root or root in resolved.parents or resolved in root.parents:
        raise PluginEvalPrepError(
            "output directory must not be inside the repository or its ancestor"
        )
    if resolved.exists():
        marker = resolved / MARKER
        if not resolved.is_dir() or marker.is_symlink() or not marker.is_file():
            raise PluginEvalPrepError(
                "existing output is not an owned eval tree; choose a new --out"
            )
        ownership = read_json(marker)
        entries = ownership.pop("entries", None)
        if ownership != {
            "version": 1,
            "owner": "cc-thingz-plugin-evals",
            "path": str(resolved),
        }:
            raise PluginEvalPrepError("invalid plugin eval output ownership marker")
        actual = sorted(
            path.relative_to(resolved).as_posix()
            for path in resolved.rglob("*")
            if path != marker
        )
        if entries != actual or any(path.is_symlink() for path in resolved.rglob("*")):
            raise PluginEvalPrepError(
                "owned output contains unexpected or missing entries; "
                "choose a new --out"
            )
    return resolved


def prepare(package: str, out: Path) -> tuple[int, int]:
    out = validate_output(out)
    source = DIST_DIR / SOURCE_TARGET / package
    if not source.is_dir():
        raise PluginEvalPrepError(f"no compiled {SOURCE_TARGET} package: {package}")
    report = inventory()
    entries = [e for e in report["active"] if e["skill"].split("/")[0] == package]
    if not entries:
        raise PluginEvalPrepError(
            f"no plugin eval fixtures found for package: {package}"
        )
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(
        source,
        out,
        ignore=shutil.ignore_patterns("evals", "node_modules", "__pycache__"),
    )
    (out / "evals").mkdir(exist_ok=True)
    for entry in entries:
        skill = entry["skill"].split("/", 1)[1]
        shutil.copytree(FIXTURES_DIR / package / skill / "evals", out / "evals" / skill)
    cases = sum(len(entry["cases"]) for entry in entries)
    (out / "inventory.json").write_text(
        json.dumps({"package": package, "active": entries, "cases": cases}, indent=2)
        + "\n",
        encoding="utf-8",
    )
    (out / MARKER).write_text(
        json.dumps(
            {
                "version": 1,
                "owner": "cc-thingz-plugin-evals",
                "path": str(out),
                "entries": sorted(
                    path.relative_to(out).as_posix() for path in out.rglob("*")
                ),
            }
        ),
        encoding="utf-8",
    )
    return len(entries), cases


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", required=False, help="package id, e.g. git-flow")
    parser.add_argument(
        "--out", type=Path, default=DEFAULT_OUT, help="owned scratch output directory"
    )
    parser.add_argument(
        "--inventory",
        action="store_true",
        help="print coverage JSON without writing files",
    )
    args = parser.parse_args(argv)
    try:
        if args.inventory:
            print(json.dumps(inventory(), indent=2))
            return 0
        if not args.package:
            raise PluginEvalPrepError("--package is required unless --inventory")
        skills, cases = prepare(args.package, args.out)
        print(
            f"prepared {skills} skill(s), {cases} case(s) for {args.package} "
            f"from {SOURCE_TARGET} at {args.out}"
        )
    except (PluginEvalPrepError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
