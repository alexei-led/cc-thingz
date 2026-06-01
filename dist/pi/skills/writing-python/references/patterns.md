# Python patterns

Use these defaults only when the project has no stronger local convention.

## Project shape

- Treat `pyproject.toml` as the source of truth for Python version, tooling, scripts, and dependencies.
- Prefer `src/` layout for packages in new projects.

## Modules

- Add a module docstring when the module has non-obvious responsibility or orchestration.
- Use clear names: `user_id`, not `id` or `uid` when the domain is user identity.

## Interfaces

Define narrow protocols at the consumer when the consumer needs only a small surface.

```python
from typing import Protocol


class UserStore(Protocol):
    def get(self, user_id: str) -> User | None: ...
    def save(self, user: User) -> None: ...
```

Use concrete classes directly when no seam is needed. Do not invent protocols for one-off calls.

## Data shapes

Use dataclasses for small domain values and config objects.

```python
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class StatusUpdate:
    raw_text: str
    display_label: str
    is_interactive: bool = False
```

Use `TypedDict` at JSON/dict boundaries that recur.

```python
from typing import NotRequired, TypedDict


class UserPayload(TypedDict):
    id: str
    name: str
    email: NotRequired[str]
```

## Typing

- Use precise collection interfaces: `Sequence[str]` for read-only inputs, `list[str]` for mutation.
- Use `Literal` for small closed string sets that drive behavior.
- Use PEP 695 generics in 3.12+ code.
- Keep legacy `TypeVar` style when editing pre-3.12 modules.

```python
from collections.abc import Sequence
from typing import Literal


def first[T](items: Sequence[T]) -> T | None:
    return items[0] if items else None

type OutputFormat = Literal["json", "csv", "text"]
```

## Control flow

Prefer early validation over nested conditionals.

```python
def process_order(order: Order | None) -> Result:
    if order is None:
        raise ValueError("order required")
    if not order.items:
        raise ValueError("order must have items")
    return save_order(order)
```

Use `match` for structured variants, not for simple equality chains.

## Errors

Raise in core code; translate at boundaries.

```python
import json
from pathlib import Path


class ConfigError(Exception):
    """Configuration cannot be parsed or validated."""


def read_config(path: Path) -> Config:
    try:
        return parse_config(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ConfigError(f"invalid config: {path}") from exc
```

Boundary handlers may catch broad exceptions when they convert to an exit code, HTTP response, log entry, or rollback and re-raise.

## Async

- Use `asyncio.TaskGroup` for sibling tasks that should fail together.
- Use `asyncio.timeout` around external waits.
- Track background task exceptions; do not silently drop them.

## Configuration

Represent config as an explicit object and pass it in. Avoid hidden global config unless the project already uses it.

```python
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Self


@dataclass(frozen=True, slots=True)
class Config:
    api_url: str
    port: int = 8080

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> Self:
        return cls(api_url=env["API_URL"], port=int(env.get("PORT", "8080")))
```

Precedence for user-facing tools: CLI flag > env var > config file > default.

## Context managers and files

- Use context managers for resources with cleanup.
- Use `pathlib.Path` for filesystem paths.
- Sort glob results when order affects output or tests.

```python
from pathlib import Path


def find_inputs(directory: Path) -> list[Path]:
    return sorted(directory.glob("**/*.json"))
```
