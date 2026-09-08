#!/usr/bin/env python3
"""Build an owned temporary eval tree; report active, archived, and uncovered skills."""

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = next(
    p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").is_file()
)
DIST_DIR = ROOT / "dist"
EVALS_DIR = ROOT / "tests" / "skill-evals"
DEFAULT_OUT = Path("/tmp/cc-thingz-skill-eval-root")
SOURCE_TARGET = "claude"
MARKER = ".cc-thingz-eval-owner.json"


class EvalPrepError(Exception):
    """Skill eval preparation failed."""


def read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise EvalPrepError(f"cannot read {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise EvalPrepError(f"expected JSON object: {path}")
    return data


def fixture_count(path: Path) -> int:
    data = read_json(path)
    cases = data.get("evals")
    if not isinstance(cases, list) or not cases:
        raise EvalPrepError(f"no evals defined: {path}")
    ids = set()
    for case in cases:
        if not isinstance(case, dict):
            raise EvalPrepError(f"invalid eval case: {path}")
        case_id = case.get("id")
        if not isinstance(case_id, str) or not case_id or case_id in ids:
            raise EvalPrepError(f"missing or duplicate eval id: {path}")
        ids.add(case_id)
        if not case.get("prompt") or not any(
            case.get(key)
            for key in ("assertions", "expected_output", "tool_assertions")
        ):
            raise EvalPrepError(f"missing prompt or assertions: {path}: {case_id}")
    if data.get("skill_name") != path.parents[1].name:
        raise EvalPrepError(f"fixture skill_name does not match directory: {path}")
    return len(cases)


def inventory() -> dict:
    compiled = {
        f"{path.parents[2].name}/{path.parent.name}": path.parent
        for path in sorted((DIST_DIR / SOURCE_TARGET).glob("*/skills/*/SKILL.md"))
    }
    active = []
    for path in sorted(EVALS_DIR.glob("*/*/evals/evals.json")):
        identity = f"{path.parents[2].name}/{path.parents[1].name}"
        if identity not in compiled:
            raise EvalPrepError(
                f"fixture has no compiled {SOURCE_TARGET} skill: {identity}"
            )
        active.append({"skill": identity, "evals": fixture_count(path)})
    if not active:
        raise EvalPrepError(f"no skill eval fixtures found under {EVALS_DIR}")
    migration_file = EVALS_DIR / "migrations.json"
    migrations = (
        read_json(migration_file).get("entries", []) if migration_file.exists() else []
    )
    archives = {
        entry["destination"]: entry
        for entry in migrations
        if entry.get("status") == "archived" and entry.get("reason")
    }
    actual_archives = {
        path.relative_to(EVALS_DIR).as_posix(): path
        for path in sorted((EVALS_DIR / "archive").glob("*/*/evals/evals.json"))
    }
    if archives.keys() != actual_archives.keys():
        raise EvalPrepError("archived fixtures must exactly match migrations.json")
    archived = []
    for name, path in actual_archives.items():
        count = fixture_count(path)
        if archives[name].get("evals") != count:
            raise EvalPrepError(f"archived fixture count changed: {name}")
        archived.append(
            {"fixture": name, "evals": count, "reason": archives[name]["reason"]}
        )
    covered = {entry["skill"] for entry in active}
    return {
        "source_target": SOURCE_TARGET,
        "active": active,
        "archived": archived,
        "uncovered_skills": sorted(compiled.keys() - covered),
        "skills": len(active),
        "evals": sum(entry["evals"] for entry in active),
    }


def validate_output(out: Path) -> Path:
    if out.is_symlink():
        raise EvalPrepError("output directory must not be a symlink")
    resolved = out.resolve()
    root = ROOT.resolve()
    if resolved == root or root in resolved.parents or resolved in root.parents:
        raise EvalPrepError(
            "output directory must not be inside the repository or its ancestor"
        )
    if resolved.exists():
        marker = resolved / MARKER
        if not resolved.is_dir() or marker.is_symlink() or not marker.is_file():
            raise EvalPrepError(
                "existing output is not an owned eval tree; choose a new --out"
            )
        ownership = read_json(marker)
        entries = ownership.pop("entries", None)
        if ownership != {
            "version": 1,
            "owner": "cc-thingz-skill-evals",
            "path": str(resolved),
        }:
            raise EvalPrepError("invalid eval output ownership marker")
        actual = sorted(
            path.relative_to(resolved).as_posix()
            for path in resolved.rglob("*")
            if path != marker
        )
        if entries != actual or any(path.is_symlink() for path in resolved.rglob("*")):
            raise EvalPrepError(
                "owned output contains unexpected or missing entries; "
                "choose a new --out"
            )
    return resolved


def prepare(out: Path) -> tuple[int, int]:
    out = validate_output(out)
    report = inventory()
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    for entry in report["active"]:
        plugin, skill = entry["skill"].split("/")
        source = DIST_DIR / SOURCE_TARGET / plugin / "skills" / skill
        dest = out / plugin / "skills" / skill
        shutil.copytree(
            source,
            dest,
            ignore=shutil.ignore_patterns("evals", "node_modules", "__pycache__"),
        )
        shutil.copytree(EVALS_DIR / plugin / skill / "evals", dest / "evals")
    (out / "inventory.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    (out / MARKER).write_text(
        json.dumps(
            {
                "version": 1,
                "owner": "cc-thingz-skill-evals",
                "path": str(out),
                "entries": sorted(
                    path.relative_to(out).as_posix() for path in out.rglob("*")
                ),
            }
        ),
        encoding="utf-8",
    )
    return report["skills"], report["evals"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
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
        else:
            skills, evals = prepare(args.out)
            print(
                f"prepared {skills} skill(s), {evals} eval(s) "
                f"from {SOURCE_TARGET} at {args.out}"
            )
            report = read_json(args.out / "inventory.json")
            archived_count = sum(item["evals"] for item in report["archived"])
            print(
                f"archived: {archived_count} eval(s); "
                f"uncovered skills: {', '.join(report['uncovered_skills']) or 'none'}"
            )
    except (EvalPrepError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
