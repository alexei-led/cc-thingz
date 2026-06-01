# Python principles

Read before generating or changing Python code.

## Dependency stance

- Prefer stdlib and existing project dependencies.
- Add a package only for a concrete requirement, not convenience.
- Match the package manager and lockfile already in use.

## Typing

- Use `X | Y`, `list[T]`, `dict[K, V]`, and PEP 695 syntax when the project target allows it.
- Avoid unbounded `Any`; isolate and validate untyped inputs at boundaries.
- Use `TypedDict`, `dataclass`, or small value objects for recurring data shapes.
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

## Logging

- Use the project's logger for diagnostics.
- Use stdlib `logging` for new code unless the project already uses another logger.
- Do not print diagnostics from library or domain code.
