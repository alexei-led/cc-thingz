#!/usr/bin/env python3
"""Build a temporary agent-skills-eval tree from compiled skills and test fixtures."""

import argparse
import json
import shutil
from pathlib import Path

ROOT = next(
    p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").is_file()
)
DIST_DIR = ROOT / "dist"
EVALS_DIR = ROOT / "tests" / "skill-evals"
DEFAULT_OUT = Path("/tmp/cc-thingz-skill-eval-root")

SOURCE_TARGET = "claude"


class EvalPrepError(Exception):
    """Skill eval preparation failed."""


def copy_skill(plugin: str, skill: str, out: Path) -> Path | None:
    """Copy a compiled skill into the eval tree, or return None when absent.

    A missing compiled source means the package no longer exports the fixture;
    return None so the evaluator can skip it without aborting.
    """
    source = DIST_DIR / SOURCE_TARGET / plugin / "skills" / skill
    if not source.is_dir():
        return None
    if not (source / "SKILL.md").is_file():
        raise EvalPrepError(f"missing SKILL.md: {source.relative_to(ROOT)}")

    dest = out / plugin / "skills" / skill
    if dest.exists():
        shutil.rmtree(dest)

    def ignore(_dir: str, names: list[str]) -> set[str]:
        ignored = {"evals", "node_modules", "__pycache__"}
        return {name for name in names if name in ignored}

    shutil.copytree(source, dest, ignore=ignore)
    return dest


def copy_evals(eval_root: Path, skill_dest: Path) -> int:
    eval_file = eval_root / "evals" / "evals.json"
    if not eval_file.is_file():
        raise EvalPrepError(f"missing evals/evals.json: {eval_root.relative_to(ROOT)}")

    with eval_file.open("r", encoding="utf-8") as file:
        data = json.load(file)
    eval_count = len(data.get("evals", [])) if isinstance(data, dict) else 0
    if eval_count == 0:
        raise EvalPrepError(f"no evals defined: {eval_file.relative_to(ROOT)}")

    shutil.copytree(eval_root / "evals", skill_dest / "evals")
    return eval_count


def prepare(out: Path) -> tuple[int, int]:
    if out == ROOT or ROOT in out.parents:
        raise EvalPrepError("output directory must not be inside the repository")

    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True, exist_ok=True)

    skill_count = 0
    eval_count = 0
    for eval_file in sorted(EVALS_DIR.glob("*/*/evals/evals.json")):
        skill_root = eval_file.parents[1]
        plugin = skill_root.parent.name
        skill = skill_root.name
        skill_dest = copy_skill(plugin, skill, out)
        if skill_dest is None:
            continue
        eval_count += copy_evals(skill_root, skill_dest)
        skill_count += 1

    if skill_count == 0:
        rel_evals_dir = EVALS_DIR.relative_to(ROOT)
        raise EvalPrepError(f"no skill eval fixtures found under {rel_evals_dir}")

    return skill_count, eval_count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help=f"output directory (default: {DEFAULT_OUT})",
    )

    args = parser.parse_args()

    try:
        skills, evals = prepare(args.out.resolve())
    except EvalPrepError as exc:
        print(f"ERROR: {exc}")
        return 1

    print(
        f"prepared {skills} skill(s), {evals} eval(s) "
        f"from {args.source_dir} at {args.out}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
