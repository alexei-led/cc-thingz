# Python Testing

## Pytest Setup

- New config: `testpaths`, `--import-mode=importlib`, `--strict-markers`, `-ra`.
- Mark slow tiers (`integration`, `e2e`, `live`) and keep them out of the default run.
- Add `pytest-asyncio`, `pytest-cov`, `pytest-timeout`, `pytest-xdist`, `pytest-mock`, or Hypothesis only when tests need them or the project already has them.
- With `pytest-asyncio` in `asyncio_mode = "auto"`, async tests need no marker.
- Keep coverage in a dedicated command or job, not the edit loop.

## Style

- `pytest.param(..., id="...")` when case names make failures readable.
- Factory fixtures for data with per-test variation. Widen fixture scope only for immutable setup. Use autouse only for isolation every test needs.
- Prefer `tmp_path` over mocking the local filesystem.
- Mock with `spec`/`autospec`, and patch where the name is looked up, not where it is defined.
- CLIs: Click's `CliRunner`, or call `main(argv)` and assert exit code plus `capsys` output. Spawn a subprocess only when `main(argv)` cannot give the same signal.
- Hypothesis fits parsers, serializers, and normalizers with many edge cases.

## Slow Suites

- Find the cost first: `pytest -q --durations=10 --durations-min=0.5`.
- Common waste: fixed sleeps, real I/O in unit tests, repeated expensive setup, heavy import-time work. Replace waits with poll-until-condition helpers or a controlled clock.
- Use `pytest-xdist` only when configured or approved. Key shared external resources by `PYTEST_XDIST_WORKER`.
