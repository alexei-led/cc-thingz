# Python Test Slice

Use this only for Python test work. The host skill owns scope, workflow, and output.
For `performance` mode or slow-suite work, also read `python-performance.md`.

## Commands

Use project commands first. If none exist, choose the narrowest useful command:

```bash
pytest -q --maxfail=1 --tb=short
pytest -q tests/test_example.py::testcase --maxfail=1 --tb=short
uv run pytest -q --maxfail=1 --tb=short
pytest -q --durations=10 --durations-min=0.5
pytest -n auto --dist worksteal -q
pytest --collect-only -q
pytest --cov=src --cov-report=term-missing
pytest -m "not slow"
```

Run coverage only for coverage mode or when review needs it. Keep `pytest-cov`
off the hot feedback path. If coverage plugins are missing, quote the error and
continue without coverage findings.

## Learn project patterns

Before changing tests:

- Read `conftest.py`.
- Read 2-3 nearby `test_*.py` files.
- Check fixture scope, parametrization style, marks, and mock setup.
- Follow project conventions unless they are the problem.

## Behavior seams

Prefer public module, API, CLI, or service boundaries. Use narrower unit seams
only when behavior is pure, local, deterministic, and cheap.

For async code, test through async public behavior and use project-configured
pytest async support.

## Fast feedback defaults

- Use the narrowest deterministic pytest node while editing; run the broader
  project command before final output.
- Treat real sleeps, real external I/O, repeated setup, and coverage-on-default
  as test waste.
- Use `pytest-xdist` only when configured or approved. Prefer `--dist worksteal`
  for uneven durations and `loadscope` or `loadfile` only for expensive grouped
  fixtures.
- Make mutable resources per-test or per-worker. Use the xdist worker id for
  shared external names such as ports, tmux sessions, databases, queues, and fixed
  filenames:

```text
PYTEST_XDIST_WORKER
```

- Mark slow tiers (`integration`, `e2e`, `live`, `llm`, or project names) and keep
  the default local command focused on fast deterministic tests.
- Add `--durations=10 --durations-min=0.5` or the project equivalent when slow
  creep is part of the problem.

## Parametrization

Prefer `@pytest.mark.parametrize` when cases share setup and assertions. Do not
force parametrization when separate tests make distinct behavior clearer.

Good parametrized cases use readable IDs, for example `pytest.param(..., id="empty-input")`.

## Fixtures and assertions

- Keep fixture scope as narrow as correctness needs, wider only when safe and useful.
- Reuse fixtures for repeated setup that hides noise, not behavior.
- Prefer plain `assert` expressions.
- Test names should describe behavior, not implementation.
- Avoid test ordering dependencies and shared mutable state.

## Mocks

- Mock system boundaries: network, filesystem, subprocesses, time, randomness, external services.
- Patch where the object is used, not where it is defined.
- Use `spec`, `autospec`, or `create_autospec` for important boundaries.
- Use `AsyncMock` for async functions.
- Verify business-critical mock calls with exact values or targeted `call_args` checks.

## Review focus

Flag:

- private-helper tests that miss public behavior
- happy-path-only tests for meaningful logic
- duplicate scenarios that can be clearer as parametrized cases
- fixtures that hide behavior or leak state
- mocks that hide contracts or accept any business value
- missing exception, edge, permission, async, concurrency, or regression cases
- fixed sleeps instead of poll-until-condition or controlled clocks
- collection-time imports or module-level work that dominates wall time
- session or module fixtures that leak mutable state across tests
- parallelism blocked by fixed filenames, shared ports, shared databases, or order dependencies
- comments that explain obvious test code instead of improving names/setup

## Failure handling

- Import errors and collection failures are blocking.
- If `pytest` fails to run, quote output and skip coverage analysis.
- If xdist exposes failures, treat them as isolation defects unless evidence says otherwise.
- If no tests exist, report that before other findings.
