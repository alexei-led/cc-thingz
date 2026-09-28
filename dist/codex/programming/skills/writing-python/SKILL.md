---
{"description":"Idiomatic Python 3.12+ development. Use when writing Python code, CLI tools, scripts, or services. Emphasizes stdlib, type hints, fast pytest feedback, uv/ruff/pyright toolchain, optional project-adopted ty, and minimal dependencies. NOT for Go, Rust, TypeScript, or shell-only tasks.","name":"writing-python"}
---
<!-- Platform guidance for Codex -->
<!-- Use this platform's installed tool names exactly; do not translate capability references into Claude Code tool syntax. -->
<!-- When this skill references shell execution, file reads, or search, use the platform's native shell, read, and search tools. -->
<!-- If a referenced helper command or optional tool is unavailable, report the gap and continue with the platform's built-in tools. -->


# Python Development

`pyproject.toml` is the source of truth for the Python target, tools, scripts, and dependencies. Check it, `.python-version`, and CI before using 3.12-only syntax. Project conventions win over these defaults.

## Toolchain

- uv for environments and commands (`uv run`, `uv add`); never call `pip` directly. Match the lockfile already in use.
- Ruff for lint and format. Pyright for types, or `ty` only when the project has adopted it.
- pytest for tests.

## Defaults

- Stdlib before packages: `argparse`, `dataclasses`, `pathlib`, `json`, `urllib`, `logging`. Do not add Rich, pydantic, or dotenv only for polish.
- 3.12+ typing: `X | Y`, builtin generics, PEP 695 generics and `type` aliases. Keep legacy `TypeVar` style when editing pre-3.12 modules.
- `@dataclass(frozen=True, slots=True)` for small values; `TypedDict` with `NotRequired` at recurring JSON boundaries; `Protocol` owned by the consumer. Keep `dict[str, Any]` at the boundary only.
- Import collection ABCs from `collections.abc`. Take `Sequence[T]` for read-only inputs.
- Wrap errors with `raise DomainError(...) from exc`. Catch broad exceptions only where they become an exit code, response, log entry, or re-raise.
- Async: `asyncio.TaskGroup` for sibling tasks, `asyncio.timeout` around external waits. Keep references to background tasks so their exceptions surface.
- Text I/O takes an explicit `encoding`. Sort glob results when order reaches output or tests.
- Libraries log through `logging`; they never print diagnostics.

## CLIs

- `argparse` for small tools; Click or Typer only when the project already uses them.
- `main(argv: Sequence[str] | None = None) -> int`; call `asyncio.run` only there. Expose it via `[project.scripts]` and keep `python -m pkg` working.
- Config precedence: flag, env, config file, default.

## References

- [testing.md](references/testing.md): read when adding or reshaping tests, or when the suite is slow.
- [linting.md](references/linting.md): read when changing Ruff or type-checker config, or the lint/type-check commands.

Done when the relevant build/test/lint checks pass on what you changed, or you name each check that did not run and why.
