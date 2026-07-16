# Python fix reference

Use for Python defect fixes. The host skill owns the full fix workflow; this file adds language-specific repro commands and key failure patterns.

## Repro and narrow loop

Find the fastest reliable failing signal first:

```bash
uv run pytest tests/test_module.py::TestClass::test_name -xvs
uv run pytest tests/ -k "test_name" -x
uv run ruff check path/to/file.py
uv run pyright path/to/file.py
```

Use the narrowest test filter while editing. Run `uv run pytest tests/ -q` or the project gate before final output. Prefer `uv run` when `pyproject.toml` manages the environment; fall back to `.venv/bin/pytest` or `python -m pytest`.

## Key failure patterns

- `None` returned from a lookup or optional arg and dereferenced without guard.
- Mutable default argument (`def f(x=[])`) shared across calls.
- Broad `except Exception` or bare `except:` hiding the real error.
- Blocking I/O (`requests.get`, `open`, `subprocess.run`) inside an `async def` without `await` or an executor.
- Timezone-naive `datetime` compared to timezone-aware; use UTC or consistent tz throughout.
- Off-by-one in slice boundaries or pagination `offset`/`limit` calculations.

## Verification

Before claiming fixed:

- Failing test or repro no longer fails.
- `ruff check` and `ruff format --check` exit clean on changed files.
- `pyright` exits clean (or shows no new errors) on changed files.
- No new deprecation or runtime warnings in test output.
