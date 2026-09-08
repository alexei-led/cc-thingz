# Runtime reliability and upgrading to 6.9

## Automatic checks

SessionStart reports project context and never deletes or compresses global plans,
todos, or logs. Retention belongs to user-managed maintenance.

Post-edit lint and Stop tests use focused checks by default. Missing support is
reported as skipped or unsupported rather than passing or silently running a
whole-project command. Set `HOOK_PROJECT_FALLBACK=1` to opt into existing project
Make/package fallback commands; `TEST_RUNNER_FULL=1` explicitly requests full
tests. These options are declared in the portable hook environment.

Smart-lint reads native or Pi JSON once and honors its project cwd, file paths,
and session identity. Guard hooks inspect ordinary git global options and both
patch rename paths. They prevent common mistakes; they do not sandbox arbitrary
shell programs.

## Pi defaults

Plan-mode shell accepts a deliberately small inspection subset. Shell expansion,
composition, unknown flags, and mutating command forms are rejected. Use native
read/search tools for other inspection. This policy is not an OS sandbox.

Hook cancellation uses POSIX process groups on macOS/Linux and waits for cleanup.
Windows execution is explicitly unsupported by this runner rather than claiming
that terminating one shell cleans up its descendants.

The structured-output demonstration remains packaged for compatibility, but
registers no tool by default. Set `CC_THINGZ_STRUCTURED_OUTPUT=1` before starting
Pi to opt into its fixed headline/summary/actionItems schema.

The regex skill suggestion hook can be disabled with `HOOK_SKILL_ENFORCER=0`.
Offline routing fixtures measure its suggestions, not whether a model follows
them or completes the task. See [skill evals](skill-evals.md).

## Helpers

- Worktree setup follows packageManager and lockfiles, uses frozen installs and
  uv, and refuses ambiguous/missing lockfiles instead of choosing a package manager.
- Playwright uses a project dependency or a pinned user cache. Browser setup is
  explicit; plugin directories remain unchanged. Chromium sandboxing is on unless
  `PLAYWRIGHT_SKILL_NO_SANDBOX=1` is explicitly set for an environment requiring it.
- BigQuery dry-run reports bytes by default. Monetary estimates require an explicit
  `--price-per-tib`; `--max-bytes` and `--max-usd` are noninteractive thresholds.
- specctl rejects blocked tasks and preserves the original session on repeated
  start. Its completion text remains human/agent evidence, not attestation.

## Installation and verification

Use [doctor](doctor.md) to identify old package copies and missing resources.
Cached copies are not proof that a plugin is enabled. Review its migration map;
do not delete unknown user caches automatically.

Doctor emits a small versioned check contract with passed, failed, skipped, and
unsupported outcomes and reasons. This is the first reusable verification result
surface. A shared execution planner is deliberately deferred until consumers and
scope rules have been demonstrated; no new scheduler is required.

Builds use `.agentbundler-version`. Run `scripts/setup/install-agbun.sh` when the
installed compiler differs. The separate upstream canary does not alter the pin.
CI/release require lockfile-pinned Claude/Codex/Pi install and Pi resource-loading
smoke, plus generated hook-adapter checks. Credential-bound vendor events remain
separate from those contracts.
