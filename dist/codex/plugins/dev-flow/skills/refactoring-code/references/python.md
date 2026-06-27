# Python refactoring reference

Use for Python behavior-preserving refactors. The host skill owns the scope-mapping workflow and output contract; this file adds language-specific mapping tools, safety gates, and caveats.

## Scope mapping

Before editing:

- Use `rg` to find all `import X`, `from X import Y`, and `X.method()` call sites before renaming.
- For module moves or renames, check `pyproject.toml` entry points, `__init__.py` re-exports, and any `importlib` or `__import__` dynamic imports.
- For class or function renames, check serialization: `pickle`, `cloudpickle`, or `joblib`-persisted objects embed the fully qualified class name.
- Pyright or Pylance rename-symbol can locate static references; use `rg` for string-based `getattr(obj, 'method_name')` and `importlib.import_module` patterns.

## Verification gate

```bash
uv run ruff check path/to/changed/
uv run pyright path/to/changed/
uv run pytest tests/ -q
```

Run ruff and pyright before each batch. Run the full pytest suite before final output.

## Key caveats

- Renaming a public function or class is a breaking change for downstream packages; keep the old name as a deprecated alias when the module is a library.
- Moving a module changes its import path; check `from old.path import X` and dynamic import strings.
- Dataclass or `attrs` field renames break serialization keys unless `field(alias=...)` or an explicit `__init__` is added.
- `__all__` in `__init__.py` controls what `from pkg import *` exports; update it when renaming or moving public symbols.
- `@property`, `__dunder__` renames, and descriptor protocol changes have subtle behavioral side effects; verify with behavior tests at the public seam.
