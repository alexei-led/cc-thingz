# Python Refactoring Caveats

- Pyright rename finds static references; search separately for `getattr(obj, "name")`, `importlib.import_module`, and `__import__` strings.
- Module moves: check `pyproject.toml` entry points, `__init__.py` re-exports, and `__all__`.
- `pickle`, `cloudpickle`, and `joblib` payloads embed the fully qualified class name; renaming or moving a class breaks stored objects.
- Dataclass, `attrs`, or Pydantic field renames change serialization keys unless an alias maps the old name.
- Renaming a public library symbol breaks downstream code; keep a deprecated alias.
- Changes to `@property`, dunder methods, or descriptors alter behavior subtly; cover them with public-seam tests.
