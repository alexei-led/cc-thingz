# Python Tests

Use writing-python for toolchain commands. Read `conftest.py` before changing
fixtures.

## Patterns

- `@pytest.mark.parametrize` with readable IDs (`pytest.param(..., id="empty-input")`).
- Fixture scope as narrow as correctness needs. Reuse fixtures to hide noise, not behavior.
- Patch where the object is used, not where it is defined. Use `autospec`/`create_autospec` on important boundaries and `AsyncMock` for async.
- Test async code through its async public behavior with the project's configured async plugin.
- Import errors and collection failures are blocking.

## Speed

- Find the bottleneck with `--durations=20 --durations-min=0.5`; when collection dominates, `python -X importtime -m pytest --collect-only`.
- `pytest-cov` instruments every line; run it only for coverage work.
- `pytest-xdist` only if configured or approved. Start with `-n auto --dist worksteal` for uneven durations; `loadscope`/`loadfile`/`loadgroup` only when grouped fixtures save more than the imbalance costs. More workers do not fix time spent waiting on sleeps or I/O.
- Key shared real resources (ports, databases, tmux sessions, fixed filenames, queues) by `PYTEST_XDIST_WORKER`.
- Replace `time.sleep`/`asyncio.sleep` with poll-until-condition helpers (small interval, hard timeout), or freeze time with the project's clock tool. Lower test-only timeouts so failure paths are fast too.
- Session or module fixtures only for immutable setup; for costly mutable artifacts (git repos, populated databases), build once and copy per test.
- Move heavy import-time work into fixtures. New pytest config: explicit `testpaths` and `--import-mode=importlib`.
- Stub expensive autouse behavior in unit tests; opt in to the real thing where it is under test.
- Mark slow tiers (`integration`, `e2e`, `live`, `llm`) and keep the default command on the fast tier. Use `--last-failed` in the edit loop.
- Mature suites can add a hook that fails non-slow tests above an env-tunable wall-time ceiling.
