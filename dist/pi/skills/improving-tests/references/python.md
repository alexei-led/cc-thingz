# Python Test Slice

Use this only for Python test work. The host skill owns scope, workflow, and output.

## Commands

Use project commands first. If none exist, choose the narrowest useful command:

```bash
pytest -v
uv run pytest -v
pytest --cov=src --cov-report=term-missing
pytest -m "not slow"
```

Run coverage only for coverage mode or when review needs it. If coverage plugins
are missing, quote the error and continue without coverage findings.

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
- comments that explain obvious test code instead of improving names/setup

## Failure handling

- Import errors and collection failures are blocking.
- If `pytest` fails to run, quote output and skip coverage analysis.
- If no tests exist, report that before other findings.
