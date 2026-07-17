# Python Test Performance

Use this for `performance` mode or any Python pytest suite that is too slow for
an agent feedback loop. The host skill owns the generic performance workflow and
quality guardrails; this file adds pytest-specific tactics.

## Measurement commands

Prefer project wrappers. If none exist, use the closest pytest command:

```bash
pytest -q --maxfail=1 --tb=short
pytest -q --durations=20 --durations-min=0.5
pytest --collect-only -q
python -X importtime -m pytest --collect-only
pytest -n auto --dist worksteal -q
```

Run coverage only when measuring coverage. `pytest-cov` instruments execution and
is usually too expensive for the hot path.

## Parallelism

- Use `pytest-xdist` when the project already has it, or ask before adding it.
- Start with `-n auto --dist worksteal` for uneven test durations.
- Use `loadscope`, `loadfile`, or `loadgroup` only when expensive grouped
  fixtures save more time than they cost in worker imbalance.
- Treat xdist failures as isolation bugs until proven otherwise.
- Key shared real resources by the xdist worker id:

```text
PYTEST_XDIST_WORKER
```

Apply it to ports, session names, databases, temp dirs, fixed filenames, queues,
and caches.

Do not add more workers when wall time is mostly waiting on sleeps, network,
subprocesses, or external services. Remove the wait instead.

## Remove real-time waits

- Replace fixed `time.sleep()` and `asyncio.sleep()` in tests with
  poll-until-condition helpers using a small interval and a hard timeout.
- Freeze or move the clock with `freezegun`, `time-machine`, or an injected clock
  when the project already uses one.
- Lower test-only timeouts through config or environment so failure paths are
  fast too.

## Mock only slow boundaries

Mock system boundaries for correctness and speed:

- network
- filesystem when `tmp_path` is not cheap enough
- subprocesses
- clocks and randomness
- external databases, queues, APIs, and services

Do not mock internal domain collaboration when real objects are cheap. That makes
tests brittle and can hide behavior regressions.

## Reduce setup cost

- Use session or module fixtures only for immutable reusable setup.
- Keep mutable fixtures function-scoped or copy from a session-scoped template.
- Prefer build-once, copy-per-test for costly artifacts such as git repos,
  project trees, generated files, or populated databases.
- Cache process-level expensive pure computation with `functools.lru_cache(maxsize=1)`.
- Stub expensive autouse behavior by default in unit tests; opt in to the real
  behavior only where it is the behavior under test.

## Keep collection cheap

- Move heavy import-time work into fixtures or functions.
- Use explicit `testpaths` and `--import-mode=importlib` for new pytest config.
- Use `python -X importtime -m pytest --collect-only` when collection is a large
  share of wall time.
- Lazy-import large optional dependencies when that does not hide runtime errors.

## Tier and select

- Mark slow tiers: `integration`, `e2e`, `live`, `llm`, or project equivalents.
- Keep the default local command on the fast deterministic tier.
- Use `--last-failed`, focused node IDs, or project-supported incremental tools
  for the edit loop.
- Run the full relevant suite at the end or report why it was skipped.

## Guard against regression

Prefer cheap visibility first:

```bash
pytest -q --durations=10 --durations-min=0.5
```

For mature suites, add a pytest hook that fails non-slow-tier tests above an
environment-tunable wall-time ceiling. Exempt marked slow tiers explicitly.

Cheap runner hygiene:

- `PYTHONDONTWRITEBYTECODE=1`
- `-p no:cacheprovider` only when `--last-failed` and cache features are not used
- disable unused legacy plugins in the local hot path
