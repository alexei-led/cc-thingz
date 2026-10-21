# Runtime defaults

## Automatic checks

SessionStart reports project context and never deletes or compresses global plans,
todos, or logs. Retention belongs to user-managed maintenance.

Post-edit lint and Stop tests use focused checks by default. Missing support is
reported as skipped or unsupported rather than passing or silently running a
whole-project command. Set `HOOK_PROJECT_FALLBACK=1` to opt into existing project
Make/package fallback commands; `TEST_RUNNER_FULL=1` explicitly requests full
tests. These options are declared in the portable hook environment.

Stop tests carry a wall-clock budget (`TEST_RUNNER_TIMEOUT_SECS`, default 90s,
kept below the hook's 120s harness timeout) shared across every test command
in the run. A command that would exceed it is killed, along with any children
it spawned, and reported as `skipped: timeout` rather than left to hang until
the harness force-kills the hook with no output. A Stop with nothing new to
test (no state since the last run, an unchanged working tree) exits immediately
instead of re-running the same tests. The kill targets the test command's
process group; a process that detaches into its own session (`setsid`, a
Gradle daemon left running in the background) is not reached by it.
"Unchanged" is decided by a tree fingerprint (tracked diff content plus
untracked file names), recomputed with a full `git diff HEAD` on most
Stops. Known limits: an in-place edit to an untracked file that keeps its
name isn't detected, and an edit made by something else while the hook is
still running can get folded into the fingerprint instead of triggering a
retest on the next Stop.

JavaScript and TypeScript tooling is selected without per-tool environment flags.
Project configs and package declarations win. Without them, smart-lint uses the
available formatter in `Oxfmt -> Biome -> Prettier` order and linter in
`Oxlint -> Biome -> ESLint` order. It runs one formatter and one linter per file.
The pre-push hook runs `make lint`, so the same non-mutating linter selection is
checked before a push. The repository helper discovers top-level JS/TS roots
such as `src/`, `test/`, and `tests/`; it skips a project with no JS/TS roots.

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

Personal messaging and plan-review integrations are user-owned. The fixed-schema
structured-output example and todo extension are no longer shipped. Use pi-tasks
for tracking; durable plan-exec uses native pi-subagents without Bridge.

Skill selection uses the host's native catalog, not a keyword hook. Retained
routing prompts are fixtures, not proof of native selection accuracy. See
[skill evals](skill-evals.md).

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

## Real-project verification

The released tooling was checked without modifying tracked files in:

- `ccgram` — Ruff lint and tests passed.
- `reflex` — Ruff and format checks passed; Pyright still needs the generated
  local imports and optional dependencies available.
- `pumba` — golangci-lint reported two existing `gci` fixes; Go tests were
  blocked by a Podman temporary-socket path limit.
- `pi-model-router` — Oxlint completed with warnings.
- `pi-subagents-skill-layout` — the project Biome check passed.

`omni` is intentionally excluded from this smoke pass because it is a large
monorepo. These checks are evidence of integration, not a replacement for each
project's own CI gate.

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

## Measurement

Measure isolated hook startup/input handling without touching user config,
invoking a model, or running project linters:

```bash
uv run python scripts/diagnostics/measure-hooks.py --runs 5
```

The JSON records median/min/max wall time for a safe file-protection check,
a 1 MiB smart-lint payload with lint disabled, and test-runner with no mapped
tests. Compare the same command on the same machine and input; process startup
is included. These are not end-to-end agent latency or model-quality scores.
CI checks the report contract, not a machine-dependent timing threshold.

Regression tests separately verify one smart-lint payload parse, one notification
parse, bounded Pi output aggregation, and no payload inspection when no hook
matches. Use the existing doctor for disk inventory; cached copies do not prove
which plugins are active. Native skill selection and model/effort comparisons
need real host eval runs: see [skill evals](skill-evals.md). Change one variable
at a time and record task success, scope adherence, verification quality, tool
calls, cost and latency. Provider/model aliases are selected identities, not
server-confirmed backends.
