# Python Review Focus

Use writing-python for toolchain commands. Check `pyproject.toml`,
`.python-version`, and CI before any version-gated claim.

- Mutable defaults and module-level mutable state; broad `except` that hides failures or drops the cause.
- Type hints that do not match runtime shape at boundaries.
- `eval`, `exec`, `pickle`, `yaml.load`, dynamic import, or `shell=True` on untrusted input.
- Blocking I/O inside `async def`; network or subprocess calls without timeout.
- Naive vs aware `datetime` mixing; pagination off-by-one.
- Unbounded caches or background tasks without shutdown.
- Free-threading or subinterpreter concerns apply only when the project opts in.
- No validation library is not a finding; flag only unvalidated input reaching sensitive behavior.
