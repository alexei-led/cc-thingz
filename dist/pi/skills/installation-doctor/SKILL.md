---
{"description":"Diagnose cc-thingz plugin installations with the bundled read-only doctor. Use for missing installed skills, helpers, or hook files, stale package versions, duplicate packages, or migration from old cc-thingz packages. NOT for broad agent configuration audits or config edits; use evolving-config.","name":"installation-doctor"}
---
<!-- Pi platform guidance -->
<!-- Use installed tool names. Discover callable tools before batching independent calls in codemode; model-only UI/orchestration tools must be called directly. -->
<!-- Prefer direct read for required skill/instruction files when exposed; otherwise use Code Mode only after verifying output protection, not assumed nested-path protection. Code Mode composes calls, not durable workflows or context-mode data processing. Async subagents notify natively: yield rather than poll. -->


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
- `hook-files` fails when a hook registration names a plugin file that is not
  on disk. A running session keeps the plugin root it started with; after a
  plugin update replaces that versioned directory, its hooks exit 127 or deny
  with "can't open file" even though the new install passes. Restart those
  sessions.
- Hook support, helper dependencies, active plugins, and effective permissions
  remain unsupported by static inventory; exit 0 does not verify them.
- Report missing Python or unreadable metadata precisely. Do not install tools,
  change configuration, or delete caches as part of this diagnostic run.

## Output

Report the inspected roots, baseline release, confirmed findings with paths,
skipped or unsupported checks, and the next corrective action. Keep hook
commands and credential contents out of the response.
