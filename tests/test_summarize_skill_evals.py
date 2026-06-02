from __future__ import annotations

import json
from pathlib import Path

from conftest import _load

summarize_skill_evals = _load("summarize-skill-evals.py")


def _write_grading(
    iteration: Path,
    skill: str,
    eval_slug: str,
    mode: str,
    passed: int,
    failed: int,
) -> Path:
    grading_dir = iteration / skill / eval_slug / mode
    grading_dir.mkdir(parents=True)
    (grading_dir / "outputs").mkdir()
    (grading_dir / "outputs" / "output.txt").write_text(
        "model output", encoding="utf-8"
    )
    grading_path = grading_dir / "grading.json"
    grading_path.write_text(
        json.dumps(
            {
                "summary": {"passed": passed, "failed": failed},
                "assertion_results": [
                    {"passed": True, "text": "good", "evidence": "ok"},
                    {
                        "passed": False,
                        "text": "missing verification",
                        "evidence": "no command shown",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    return grading_path


def test_latest_iteration_uses_highest_numeric_suffix(tmp_path):
    (tmp_path / "iteration-2").mkdir()
    (tmp_path / "iteration-10").mkdir()
    (tmp_path / "iteration-old").mkdir()

    assert summarize_skill_evals.latest_iteration(tmp_path).name == "iteration-10"


def test_collect_counts_failures_and_skill_name_from_meta(tmp_path):
    iteration = tmp_path / "iteration-1"
    skill_dir = iteration / "writing-shell"
    skill_dir.mkdir(parents=True)
    (skill_dir / "meta.json").write_text(
        json.dumps({"name": "Writing Shell"}),
        encoding="utf-8",
    )
    _write_grading(iteration, "writing-shell", "rewrite-grep", "with_skill", 2, 1)
    _write_grading(iteration, "writing-shell", "rewrite-grep", "without_skill", 1, 2)

    counts, per_skill, failures = summarize_skill_evals.collect(iteration)

    assert counts["with_skill"] == summarize_skill_evals.Counts(passed=2, failed=1)
    assert counts["without_skill"] == summarize_skill_evals.Counts(passed=1, failed=2)
    assert per_skill["Writing Shell"].with_skill.rate == 2 / 3
    assert per_skill["Writing Shell"].without_skill.rate == 1 / 3
    assert len(failures) == 2
    assert failures[0].skill == "Writing Shell"
    assert failures[0].eval_slug == "rewrite-grep"
    assert failures[0].text == "missing verification"


def test_format_counts_reports_not_run_for_missing_mode():
    assert (
        summarize_skill_evals.format_counts(
            "without_skill",
            summarize_skill_evals.Counts(),
        )
        == "without_skill: not run"
    )


def test_render_markdown_separates_actionable_and_baseline_failures(tmp_path):
    iteration = tmp_path / "iteration-1"
    _write_grading(iteration, "skill-a", "case-a", "with_skill", 0, 1)
    _write_grading(iteration, "skill-a", "case-a", "without_skill", 0, 1)
    counts, per_skill, failures = summarize_skill_evals.collect(iteration)

    report = summarize_skill_evals.render_markdown(
        iteration,
        counts,
        per_skill,
        failures,
        limit=10,
    )

    assert "## With-skill failures to fix" in report
    assert "## Baseline failures" in report
    assert "**skill-a / case-a** `[with_skill]`" in report
    assert "**skill-a / case-a** `[without_skill]`" in report
