# Python Linting

Use the project's configured commands first. Edit loop, scoped to changed files:

```bash
uv run ruff check --fix path/to/file.py
uv run ruff format path/to/file.py
uv run pyright path/to/file.py
```

Full gate before finishing:

```bash
uv run ruff check .
uv run ruff format --check .
uv run pyright        # or: uv run ty check, when the project adopted ty
```

- Fall back to the project's mypy command when that is what it configures.
- Fix the code instead of loosening Ruff rules or type strictness. Ask before changing rule config in `pyproject.toml` or `pyrightconfig.json`.
- A `# type: ignore` or `# pyright: ignore` names the rule and the reason. No blanket ignores.
- Missing imports or stubs: check `uv.lock` and declared dependencies before adding a suppression.
- Exclude generated and vendored code in config, not with ad hoc command filters.
