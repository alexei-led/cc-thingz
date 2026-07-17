# Python CLI patterns

Use this for Python command-line applications. Prefer the project's current framework.

## Framework choice

- Use `argparse` for small stdlib tools.
- Use Click when the project already uses it or the CLI needs nested commands, rich validation, or shell completion.
- Use Typer only when already adopted or type-driven commands are a clear project convention.
- Do not add Rich, Click, Typer, or dotenv only for polish.

## Boundaries

- Keep parsing, output, and exit-code mapping in the CLI layer.
- Keep domain work in plain functions that accept typed values and return typed results.
- Call `asyncio.run` only at the top-level CLI boundary.
- Return an integer exit code from `main`.

## Options and configuration

- Use env vars for secrets, endpoints, credentials, and operational defaults.
- Do not mirror every flag as an env var.
- Apply precedence: CLI flag > env var > config file > default.
- Validate at parse time when the framework supports it; otherwise validate before calling domain code.

## Output

- Use stdout for requested command output and stderr for diagnostics.
- Prefer JSON for machine-readable output.
- Use `output_format` as the Python parameter name; user-facing flags follow project convention.
- Type structured rows as `Sequence[Mapping[str, object]]` or a concrete row type.
- Keep table rendering local to the CLI layer.

## Exit codes

- Map usage errors to the project's usage-code convention.
- Map expected runtime failures to non-zero exits with user-facing messages.
- Catch broad exceptions only at the CLI boundary.
- Log unexpected exceptions when project logging exists.

## Entry points

- Expose commands through `[project.scripts]` when packaging a CLI.
- Keep `python -m mypackage` working when users may run the package directly.

## Testing

Read [testing.md](testing.md) for CLI tests.

- For Click, use `CliRunner`.
- For argparse-style CLIs, call `main(argv)` and assert exit code plus stdout/stderr behavior.
- Use isolated temp directories for filesystem side effects.
- Do not spawn a subprocess when `main(argv)` gives the same signal.
