# Test performance

Measured on 2026-10-05 against `v6.20.0` (`0c753864`), on the same macOS host:
Python 3.14.3, pytest 9.0.2, xdist 3.8.0, Bun 1.4.2. Other jobs shared the host.
These are single-run observations, not a stable benchmark or a latency guarantee.

| Full suite | Before wall time | After wall time | Results after |
| --- | ---: | ---: | --- |
| Python | 198.75 s | 132.27 s | 584 passed, 2 skipped |
| Bun | 29.35 s | 28.24 s | 313 passed |

The Python baseline had 570 passing tests and the same two skips. The Bun baseline
had 309 passing tests. Added cases cover invalid permission input, the shell
fast path, and commit-pinned external Actions. No integration tier was removed.

## Changes that reduce work

- Import the cleanup graph in six Git processes rather than repeated checkout,
  commit, and push sequences. Reuse it per worker and copy it per test.
- Run parser matrices in-process. Keep shell payload/fast-path checks and
  real-Git cleanup integration separate.
- Remove per-test rebuilds from rendered-adapter checks. Move build idempotence
  to a temporary tree to avoid concurrent writes to the checkout.
- Share commit-state setup and parameterize suspicious-path/content cases.
- Accelerate the permission timeout through a timer spy. Keep real process
  timeout, cancellation, shutdown, and descendant-kill checks.
- Poll server readiness instead of sleeping a fixed interval.
- Replace weak plan-item assertions with exact table-driven expectations.
- Run Bats suites concurrently. Isolate formatter discovery from host-installed
  tools instead of accidentally invoking a developer's formatter.

Grouping all cleanup tests on one worker created a long serial tail. A four-worker
cap also failed to improve total latency. Neither is the default: work stealing
balances tests across the automatic worker count. `PYTEST_WORKERS` remains
available for a specific machine.

## CI

CI combines Python lint, package validation, fixture inventory, and Python tests
in one job. TypeScript lint and tests share another. This removes repeated
checkout, dependency, and Agent Bundler setup without dropping gates.
The runtime smoke job uses one pytest session for its existing selections.
The shell job now runs all 160 existing Bats cases instead of only linting them.
They also run in `make ci`. CI installs Bats 1.14.0 from its pinned release
commit, not the older Ubuntu package. This adds coverage, so end-to-end CI timing is not
an equal-work comparison with v6.20.0.

External Actions are pinned to current stable release commits. Go caches in
read-only CI use `.agentbundler-version` as the dependency key. Runtime smoke
uses the locked npm download cache. Release validation and publication keep
caches disabled. Superseded branch CI runs are cancelled, not release runs.

The comparison baseline is
[CI run 37295181502](https://github.com/alexei-led/cc-thingz/actions/runs/37295181502):
Tests 48 s, Config Validation 25 s, Lint Python 24 s, Lint TypeScript 12 s,
Test TypeScript 38 s. CI Success completed 72 s after the first job started.
Job times overlap, so their sum is not pipeline latency.

`actionlint` passes. `zizmor` still flags the read-only CI caches as potential
cache poisoning because that workflow uploads advisory evaluation reports.
Those reports are not executable release inputs. Publishing uses separate,
uncached jobs. These low-confidence warnings are not reported as a clean scan.

The baseline [release run](https://github.com/alexei-led/cc-thingz/actions/runs/37295181100)
took 93 s for validation, including 56 s for `make ci`. Cloud after-times require
a completed run of the changed workflow. Local timings do not predict them.

## Commands

Before: `uv run --extra test python -m pytest tests/ -n auto --durations=30`.

After: `make test PYTEST_ARGS='--durations=15 --junitxml=/tmp/python.xml'`.
Both run the full Python suite. The updated target adds `--dist worksteal`.

Bun: `make test-ts` before and after. Timings above include command startup.
See [test organization and isolation](../tests/README.md).
