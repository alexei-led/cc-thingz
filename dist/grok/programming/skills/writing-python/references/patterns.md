# Python patterns

Use these defaults only when the project has no stronger local convention.

## Project shape

- Treat `pyproject.toml` as the source of truth for Python version, tooling, scripts, and dependencies.
- Prefer `src/` layout for packages in new projects.

## Modules

- Add a module docstring when the module has non-obvious responsibility or orchestration.
- Use domain-specific names: `user_id`, not `id` or `uid` when the domain is user identity.

## Interfaces

- Define narrow protocols at the consumer when the consumer needs only a small surface.
- Use concrete classes directly when no seam is needed.
- Do not invent protocols for one-off calls.

## Data shapes

- Use `@dataclass(frozen=True, slots=True)` for small immutable domain values and config objects.
- Use `TypedDict` at recurring JSON or dict boundaries.
- Use `NotRequired` for optional payload fields.
- Avoid `dict[str, Any]` outside boundary code.

## Typing

- Use precise collection interfaces: `Sequence[str]` for read-only inputs, `list[str]` for mutation.
- Import collection ABCs from `collections.abc`.
- Use `Literal` for small closed string sets that drive behavior.
- Use PEP 695 generics and type aliases in 3.12+ code.
- Keep legacy `TypeVar` style when editing pre-3.12 modules.

## Control flow

- Prefer early validation over nested conditionals.
- Use `match` for structured variants, not simple equality chains.

## Errors

- Raise in core code; translate at boundaries.
- Wrap config, I/O, and parse errors with a domain-specific exception and `from exc`.
- Catch broad exceptions only where they become an exit code, HTTP response, log entry, rollback, or re-raise.

## Async

- Use `asyncio.TaskGroup` for sibling tasks that should fail together.
- Use `asyncio.timeout` around external waits.
- Track background task exceptions; do not silently drop them.

## Configuration

- Represent config as an explicit object and pass it in.
- Validate required environment variables and type conversions.
- Wrap missing or invalid config values in a config-specific exception.
- Avoid hidden global config unless the project already uses it.
- Apply precedence for user-facing tools: CLI flag > env var > config file > default.

## Context managers and files

- Use context managers for resources with cleanup.
- Use `pathlib.Path` for filesystem paths.
- Use explicit encodings for text I/O.
- Sort glob results when order affects output or tests.
