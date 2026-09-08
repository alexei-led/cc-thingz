#!/usr/bin/env python3
"""Measure hook hints offline against curated prompts, without model execution."""

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = next(
    p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").is_file()
)
DEFAULT_FIXTURES = ROOT / "tests/skill-evals/routing/prompts.json"
DEFAULT_HOOK = ROOT / "src/hooks/skill-enforcer/hook.sh"


def load_cases(path: Path) -> list[dict]:
    cases = json.loads(path.read_text(encoding="utf-8"))["cases"]
    seen = set()
    if not isinstance(cases, list) or not cases:
        raise ValueError("fixtures must contain a nonempty cases list")
    for case in cases:
        if case["id"] in seen:
            raise ValueError(f"duplicate case id: {case['id']}")
        seen.add(case["id"])
        for key in ("id", "language", "prompt"):
            if not isinstance(case[key], str) or not case[key]:
                raise ValueError(f"invalid {key}")
        for key in ("required", "allowed"):
            if not isinstance(case[key], list) or not all(
                isinstance(skill, str) and skill for skill in case[key]
            ):
                raise ValueError(f"invalid {key}")
        if not set(case["required"]) <= set(case["allowed"]):
            raise ValueError(f"required hints must be allowed: {case['id']}")
    return cases


def summarize(rows: list[dict]) -> dict:
    suggested = sum(len(row["suggested"]) for row in rows)
    unexpected = sum(len(row["unexpected"]) for row in rows)
    required = sum(len(row["required"]) for row in rows)
    missing = sum(len(row["missing"]) for row in rows)
    return {
        "cases": len(rows),
        "matching_cases": sum(
            not row["unexpected"] and not row["missing"] for row in rows
        ),
        "suggested_hints": suggested,
        "unexpected_hints": unexpected,
        "required_hints": required,
        "missing_hints": missing,
        "allowed_hint_precision": (suggested - unexpected) / suggested
        if suggested
        else None,
        "required_hint_recall": (required - missing) / required if required else None,
        "nonzero_hook_exits": sum(row["returncode"] != 0 for row in rows),
    }


def evaluate(hook: Path, cases: list[dict], *, disabled: bool = False) -> dict:
    hook_hash = hashlib.sha256(hook.read_bytes()).hexdigest()
    env = os.environ.copy()
    env["HOOK_SKILL_ENFORCER"] = "0" if disabled else "1"
    rows = []
    for case in cases:
        result = subprocess.run(
            ["bash", str(hook.resolve())],
            input=json.dumps({"prompt": case["prompt"]}),
            text=True,
            capture_output=True,
            timeout=10,
            cwd=ROOT,
            env=env,
        )
        suggestions = set()
        for line in result.stdout.splitlines():
            if line.startswith("→ Consider skills: "):
                suggestions.update(line.removeprefix("→ Consider skills: ").split())
        required = set(case["required"])
        allowed = set(case["allowed"])
        rows.append(
            {
                "id": case["id"],
                "language": case["language"],
                "required": sorted(required),
                "suggested": sorted(suggestions),
                "unexpected": sorted(suggestions - allowed),
                "missing": sorted(required - suggestions),
                "returncode": result.returncode,
                "stderr": result.stderr.strip(),
            }
        )
    if hashlib.sha256(hook.read_bytes()).hexdigest() != hook_hash:
        raise ValueError("hook changed during the experiment; rerun a stable revision")
    return {
        "hook_sha256": hook_hash,
        "disabled": disabled,
        "limitations": (
            "Curated hint matches only; no model execution, task quality, cost, "
            "or representative multilingual coverage measured."
        ),
        "summary": summarize(rows),
        "by_language": {
            language: summarize([row for row in rows if row["language"] == language])
            for language in sorted({row["language"] for row in rows})
        },
        "cases": rows,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hook", type=Path, default=DEFAULT_HOOK)
    parser.add_argument("--fixtures", type=Path, default=DEFAULT_FIXTURES)
    parser.add_argument("--disabled", action="store_true", help="request hook opt-out")
    args = parser.parse_args(argv)
    try:
        report = evaluate(args.hook, load_cases(args.fixtures), disabled=args.disabled)
        report["fixtures_sha256"] = hashlib.sha256(
            args.fixtures.read_bytes()
        ).hexdigest()
        print(json.dumps(report, indent=2))
    except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
