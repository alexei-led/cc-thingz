---
name: installation-doctor
description: >-
  Diagnose cc-thingz plugin installations with the bundled read-only doctor.
  Use for missing installed skills or helpers, stale package versions, duplicate
  packages, or migration from old cc-thingz packages. NOT for broad agent
  configuration audits or config edits; use evolving-config.
---

# Installation Doctor

Inspect installed resources without a repository checkout. The helper compares
files against its bundled release catalog; it does not execute hooks or modify
installations.

## Run

1. Locate `scripts/doctor.py` relative to this installed `SKILL.md`.
2. Use an existing Python 3.12+ interpreter with `-B`. If using uv, run
   `uv run --no-project python -B <skill-directory>/scripts/doctor.py --json`.
   uv may populate its own cache; use an existing interpreter directly when the
   entire invocation must be read-only.
3. Select roots for the requested runtime. Without root options the helper
   inspects the Codex cc-thingz marketplace cache and user flat skill directories.
   For Claude or a specific installation, pass `--plugin-root <directory>`.
   Repeat `--plugin-root` or `--skill-root` for multiple locations. Any explicit
   root option restricts inspection to supplied roots.
4. Optionally pass `--config-root <.codex-directory>` to check agent profile
   presence, or `--repo <cc-thingz-checkout>` for comparison with source manifests.
5. Summarize failed checks with paths, migration suggestions, and verification
   gaps. Exit 1 means findings; exit 2 means invalid arguments.

## Interpretation

- Cached copies do not prove enabled plugins or duplicate execution. Inspect the
  runtime's enabled-plugin list before recommending removal.
- Versions are compared with the release containing this helper, not an online
  latest release. Without a containing native manifest, version checks are skipped.
- Hook support, helper dependencies, active plugins, and effective permissions
  remain unsupported by static inventory; exit 0 does not verify them.
- Report missing Python or unreadable metadata precisely. Do not install tools,
  change configuration, or delete caches as part of this diagnostic run.

## Output

Report the inspected roots, baseline release, confirmed findings with paths,
skipped or unsupported checks, and the next corrective action. Keep hook
commands and credential contents out of the response.
