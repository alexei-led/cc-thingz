# Python testing

Use this when adding or reshaping Python tests. Keep generic testing rules out of this file.

## Test design

- Test through public interfaces unless a private helper carries distinct risk.
- Prefer integration-style tests when they give a stable signal with less mocking.
- Cover happy path, invalid input, and boundary values for changed behavior.
- Delete shallow or duplicate tests when a stronger interface test covers the same behavior.
- For risky fixes, use red-green-refactor: failing regression test, minimal fix, cleanup while green.

## Pytest defaults

- Use pytest when the project has it or no framework is configured.
- For new pytest config, prefer `testpaths`, `--import-mode=importlib`, `--strict-markers`, and `-ra`.
- Mark integration tests that use real filesystem, subprocesses, or external services.
- Add plugins such as `pytest-asyncio`, `pytest-cov`, `pytest-timeout`, or Hypothesis only when tests require them.

## Parametrized cases

- Use parametrization for input/output matrices and edge cases.
- Use `pytest.param(..., id="...")` when case names improve failure output.

## Fixtures

- Use fixtures for shared setup that makes tests clearer.
- Use factory fixtures for complex data with per-test variation.
- Avoid autouse fixtures except for global isolation that every test needs.

## Mocking

- Mock only system boundaries: network, filesystem, time, randomness, subprocesses, external services.
- Prefer real internal collaborators when cheap.
- Prefer `tmp_path` over mocking local filesystem access when cheap.
- Use `spec`, `autospec`, or `create_autospec` when mocking typed collaborators.
- Patch where the object is looked up, not where it is defined.
- Assert calls only when the call is observable behavior or protects an integration contract.
- Use `pytest-mock` only when the project already has it.

## Async tests

- Use the project's async pytest setup.
- If `pytest-asyncio` sets `asyncio_mode = "auto"`, no marker is needed.

## CLI tests

- For Click, use `CliRunner`.
- For argparse-style CLIs, call `main(argv)` and assert exit code plus captured output.
- Use isolated temp directories for filesystem side effects.

## Property-based tests

Use Hypothesis for parsers, serializers, normalizers, and data transformations with many edge cases. Do not add it for one obvious example case.

## Coverage

Coverage is a signal, not the goal. Prefer a lower number backed by meaningful behavior tests over high coverage from trivial tests.
