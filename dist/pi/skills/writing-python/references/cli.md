# Python CLI patterns

Use this for Python command-line applications. Prefer the project's current framework.

## Framework choice

- Use `argparse` for small stdlib tools.
- Use Click when the project already uses it or the CLI needs nested commands, rich validation, or shell completion.
- Use Typer only when already adopted or when type-driven command definitions are a clear project convention.
- Do not add Rich, Click, Typer, or dotenv only for polish.

## Boundaries

- Keep parsing, output, and exit-code mapping in the CLI layer.
- Keep domain work in plain functions that accept typed values and return typed results.
- Call `asyncio.run` only at the top-level CLI boundary.
- Use stdout for requested command output and stderr for diagnostics.

## Options and configuration

- Use env vars for secrets, endpoints, credentials, and operational defaults.
- Do not mirror every flag as an env var.
- Apply precedence: CLI flag > env var > config file > default.
- Validate at parse time when the framework supports it; otherwise validate before calling domain code.

## Minimal argparse shape

```python
from argparse import ArgumentParser
from collections.abc import Sequence
from pathlib import Path


def main(argv: Sequence[str] | None = None) -> int:
    parser = ArgumentParser()
    parser.add_argument("input", type=Path)
    args = parser.parse_args(argv)
    process(args.input)
    return 0
```

## Minimal Click shape

```python
from pathlib import Path

import click


@click.group()
def cli() -> None:
    pass


@cli.command()
@click.argument("input_file", type=click.Path(exists=True, path_type=Path))
@click.option("--dry-run", is_flag=True)
def process(input_file: Path, dry_run: bool) -> None:
    if dry_run:
        click.echo(f"Would process {input_file}")
        return
    run_process(input_file)
```

## Output formats

- Name the option `output_format`, not `format`.
- Type structured rows as `Sequence[Mapping[str, object]]` or a concrete row type.
- Prefer JSON for machine-readable output.
- Keep table rendering local to the CLI layer.

## Exit codes

Catch broad exceptions only at the CLI boundary, where they become an exit code and user-facing message.

```python
import sys

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_USAGE = 2


class UsageError(Exception):
    """User supplied invalid CLI input."""


def main() -> int:
    try:
        run()
    except UsageError as exc:
        print(f"Usage error: {exc}", file=sys.stderr)
        return EXIT_USAGE
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return EXIT_ERROR
    return EXIT_OK
```

## Entry points

```toml
[project.scripts]
mytool = "mypackage.cli:main"
```

Keep `python -m mypackage` working when users may run the package directly.

## Testing

Read [testing.md](testing.md) for CLI tests. For Click, prefer `CliRunner`; for argparse, call `main(argv)` and assert exit code plus stdout/stderr behavior.
