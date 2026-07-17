# Python linting

Use before changing ruff config, pyright config, or Python lint/format/type-check flow.

## Fast feedback

- Use the project's configured command first.
- Prefer file- or package-scoped commands for the edit loop:

```bash
uv run ruff check path/to/file.py
uv run ruff format path/to/file.py
uv run pyright path/to/file.py
```

- Keep whole-repo lint and type-check runs out of the every-turn loop unless they are the failing signal.

## Ruff

- Run `uv run ruff check .` and `uv run ruff format --check .` before final output.
- Use `uv run ruff check --fix .` and `uv run ruff format .` to apply fixes, then re-run the check.
- Do not disable or narrow ruff rules just to make a scoped change pass. Fix the code or ask before changing `pyproject.toml` rule config.

## Pyright

- Run `uv run pyright` (or the project's configured invocation) before final output when the change touches typed code.
- Do not loosen `pyproject.toml`/`pyrightconfig.json` strictness or add blanket `# type: ignore` to silence an error. Fix the type or narrow the ignore with a reason.
- If pyright reports missing imports or stubs, check `uv.lock`/dependencies before adding a suppression.

## Do not weaken signal

- Do not lower ruff or pyright strictness just to get a green check.
- Keep generated code, vendored code, and build output excluded through normal `pyproject.toml` config rather than ad hoc command filters.
- Report missing tools directly and run the nearest configured command.

## Final gates

Use the project's configured command when present. Otherwise a solid default is:

```bash
uv run ruff check .
uv run ruff format --check .
uv run pyright
```
