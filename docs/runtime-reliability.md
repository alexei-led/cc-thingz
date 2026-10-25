# Runtime defaults

## Automatic checks

SessionStart reports project context and never deletes or compresses global plans,
todos, or logs. Retention belongs to user-managed maintenance.

Post-edit lint and Stop tests use focused checks by default. Missing support is
reported as skipped or unsupported rather than passing or silently running a
whole-project command. A file type with no installed tool is unsupported, not a
failed or incomplete check, and the lint pass line is only printed when every
selected type was checked. Pi omits that status text because it surfaces every
successful-hook stderr line as a notice; lint problems, timeouts, and genuine gaps
still appear. Set `HOOK_PROJECT_FALLBACK=1` to opt into existing project
Make/package fallback commands; `TEST_RUNNER_FULL=1` explicitly requests full tests.
These options are declared in the portable hook environment.

Automatic lint and test hooks are advisory. A failed assertion, lint diagnostic,
missing runtime, collection error, timeout, or runner crash is reported without
blocking an edit, agent completion, or requesting another model turn. A partial run
is incomplete, never passed. Explicit test commands, pre-commit/pre-push checks, CI,
and release validation retain their normal failing exit codes. File-protection, Git,
release, and permission guards retain their deny behavior; advisory feedback is not
a replacement for those guards.

Python tests use the nearest `pyproject.toml` at or below the hook cwd. Go uses its
nearest module. JS tests prefer package-local configuration and may inherit an
applicable workspace runner/configuration. Each test group runs with paths relative
to its execution directory. Go, Jest, Vitest, and Bun execution counts come from
machine-readable reports, so zero/all-skipped runs are not called passes. Other
runners report successful command completion without claiming verified test
collection. Pytest retains its exit-5 no-collection handling. Python/Go/JS lint
checks also run from the owning project. Hooks do not run dependency installers; uv
selection/execution uses no-sync behavior rather than repairing an environment
automatically.

Stop tests carry a shared wall-clock budget (`TEST_RUNNER_TIMEOUT_SECS`, default
90s, below the 120s harness timeout), including Python environment probes. Slow test
processes and their children are terminated and reported as incomplete. Lint has
per-command and whole-hook budgets. If its watchdog cannot run safely, the check is
skipped rather than run without a deadline. Captured command output is capped at 1
MiB and displayed diagnostics are byte- and line-bounded. Process groups cannot
reach a descendant that deliberately detaches into a separate session.

With usable project/session metadata, unchanged Stops are quiet and do not rerun
tests. Failed/incomplete attempts and explicit skips retain pending files but are
also suppressed for unchanged inputs, avoiding a failure loop after every turn.
Tracking state is scoped by Git worktree, session, and hook cwd. Legacy ambiguous
relative-path caches are not reused. Concurrent edit events append atomically
instead of overwriting each other's pending files. The snapshot includes tracked
diffs and untracked code/config contents; it is taken before execution so concurrent
later edits remain detectable. After repairing an external environment without
editing code, retry the reported command directly, or use `TEST_RUNNER_FULL=1` to
bypass attempt suppression and explicitly request full tests. An attempted check is
not recorded as a pass.

The portable Pi adapter supplies trusted project/session metadata and displays
hook diagnostics as informational notices and hook failures as errors, bounded and
non-blocking, without scheduling a model turn, with stderr fallback in headless
mode. Long messages keep both their beginning and final outcome;
terminal-control sequences are removed. The optional compatibility runner also
separates launch/cancellation errors from hook-authored decisions. Explicit exit-2
control decisions in user-configured hooks keep their existing semantics; shipped
advisory hooks do not emit them. Other vendor adapters retain the runtime limits
documented in [portable hook boundaries](../src/hooks/UNSUPPORTED.md).

Malformed hook input and unavailable edit targets are skipped rather than falling
back to unrelated dirty files. File contents are not parsed as extra patch targets
when explicit edit paths are present. Session context tolerates malformed helper
results and reports unavailable queries without a traceback or blocking startup.
Notifications remain best-effort and asynchronous; failed desktop delivery reports
its exit status and uses text fallback.
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
