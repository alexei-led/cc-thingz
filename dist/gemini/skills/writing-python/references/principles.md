# Python principles

Read before generating or changing Python code.

## Dependency stance

- Prefer stdlib and existing project dependencies.
- Add a package only for a concrete requirement, not convenience.
- Match the package manager and lockfile already in use.

## Typing

- Use `X | Y`, `list[T]`, `dict[K, V]`, and PEP 695 syntax for 3.12+ projects.
- Avoid unbounded `Any`; isolate and validate untyped inputs at boundaries.
- Use `TypedDict`, `dataclass`, or small value objects for recurring dict shapes.
- Use `Protocol` for consumer-owned interfaces; use ABC only for runtime enforcement.

## Control flow

- Validate early with guard clauses.
- Keep the successful path visually obvious.
- Use `match` only when it is clearer than simple conditionals.

## Errors

- Raise specific exceptions with useful context.
- Handle errors at process, CLI, API, or worker boundaries.
- Use broad `except Exception` only at boundaries or cleanup sites that log, convert, or re-raise.
- Catch multiple types with tuple syntax: `except (KeyError, ValueError) as exc:`.
- Use exception chaining when wrapping: `raise ConfigError("invalid config") from exc`.

## Logging and output

- Use the project's logger for diagnostics.
- Use stdlib `logging` for new code unless the project already uses another logger.
- CLI user output may write to stdout/stderr through the chosen CLI framework.

## Verification

Run configured tests, lint, format checks, and type checks after code changes. If a gate is absent, state that and run the closest project check.
