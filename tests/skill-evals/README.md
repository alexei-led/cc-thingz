# Skill eval fixtures

Active suites use canonical package/skill identities matching `dist/claude`.
Preparation fails if an active fixture lacks a compiled skill; run `make build`
after changing package composition. A missing suite is reported as uncovered,
not interpreted as a successful evaluation.

`migrations.json` records original fixture paths, case counts and destinations.
The September 2026 migration preserves all 74 original scenarios: 72 active
scenarios across 25 skills, and two archived learning-patterns scenarios.
Duplicate package-era suites were merged, preserving their case IDs.
reviewing-cc-config scenarios now exercise evolving-config. Obsolete
Perplexity-specific source-discovery wording was changed to platform web tools.
The retired learning-patterns skill has no direct exported replacement, so its
original fixtures remain under `archive/` with an explicit reason. Archives must
match the migration registry and are never passed to the paid evaluator.

Run the deterministic, offline inventory without creating an output tree:

```bash
uv run python scripts/evals/prepare-skill-evals.py --inventory
```

The JSON report lists active counts, archived counts with reasons, and every
compiled skill without a suite. Preparation also writes `inventory.json` beside
the copied packages. This is fixture coverage, not evidence that model behavior
passed: actual paid evaluation remains an explicit separate command.

`--out` must be outside the repository and cannot be a repository ancestor or a
symlink. The first run requires an absent directory. Subsequent runs may replace
only a tree bearing the tool's ownership marker for that exact resolved path.
Unexpected or missing entries and symlinks inside a marked tree are also rejected.
An existing unmarked directory is rejected without deletion; use a new scratch
path when migrating from the old preparer. Treat a marked tree as disposable;
never store personal files there.
