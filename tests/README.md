# Tests

## Commands

- `make test`: full Python suite, automatic worker count and work stealing.
- `make test PYTEST_WORKERS=4`: cap workers explicitly on a busy machine.
- `make test PYTEST_ARGS='--durations=30 -k cleanup'`: focused selection with timings.
- `make test-ts`: all Bun tests, with per-file isolation.
- `make test-shell`: all 160 Bats cases, four suite files in parallel. Uses Bats 1.14.0.
- `make test-fast test-ts-fast`: pre-push subsets, not release coverage.
- `make ci`: lint, validate, and check generated output before running Python
  Bun, and Bats tests concurrently.

The Python runner prints the slowest 15 tests by default. Coverage and paid
model evaluations are separate commands, not overhead on each test run.

## Boundaries

| Location | Contract |
| --- | --- |
| `test_*.py` | CLI, packaging, release, documentation, and repository contracts |
| `hooks/` | Hook decision rules and real shell/adapter integration |
| `pi-extensions/` | Bun unit tests and real subprocess lifecycle checks |
| `vendor-smoke/` | Locked runtime dependencies for CI integration checks |
| `skill-evals/` | Model-evaluation fixtures; inventory checks are offline |
| `git_helpers.py` | Shared real Git graph and hook boundary helpers |

Parser matrices call the decision engine with a failing Git subprocess boundary.
Separate shell tests cover JSON payloads, quoted command names, and the fast path.
Cleanup proofs still use real Git ancestry, squash history, worktrees, and config.

## Isolation and setup

Pytest builds generated output once in its controller before starting workers.
Tests read that tree. Build-idempotence tests use a separate temporary source
tree, so they cannot replace files while another worker reads them.

Each worker lazily imports one immutable cleanup graph with `git fast-import`.
Each test gets a copy with its own refs, config, and worktrees. Do not mutate the
template or share writable test repositories. Fixture Git commands ignore user
and system configuration, including signing and global hooks.

Bun files remain isolated because some tests mock modules or change process
globals. Only the permission timer is accelerated through the clock boundary.
Timeout and process-tree tests still launch real children and check termination.
A zombie is an exited process waiting for its parent to reap it, not a live child.

## Measuring changes

Compare the same suite and runtime versions, record pass/skip counts, and separate
test time from setup time. Use `--durations` and `--junitxml` for evidence.
Worker count and host load affect wall time. Do not infer coverage from test count,
or claim a speedup from a run that skipped checks.

See [measurements and CI changes](../docs/testing-performance.md).
