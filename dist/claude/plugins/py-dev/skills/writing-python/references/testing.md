# Python testing

Use this when adding or reshaping Python tests. Keep generic testing rules out of this file.

## Test design

- Test through public interfaces unless a private helper carries distinct risk.
- Prefer integration-style tests when they give a stable signal with less mocking.
- Cover happy path, invalid input, and boundary values for changed behavior.
- Delete shallow or duplicate tests when a stronger interface test covers the same behavior.
- For risky fixes, use red-green-refactor: failing regression test, minimal fix, cleanup while green.

## Pytest defaults

Use pytest when the project has it or no framework is configured.

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = ["--import-mode=importlib", "--strict-markers", "-ra"]
markers = [
    "integration: tests using real filesystem, subprocesses, or external services",
    "e2e: full-system tests",
]
```

Add plugins or tools such as `pytest-asyncio`, `pytest-cov`, `pytest-timeout`, or Hypothesis only when tests require them.

## Parametrized cases

Use parametrization for input/output matrices and edge cases.

```python
@pytest.mark.parametrize("email,expected_error", [
    pytest.param("user@example.com", None, id="valid"),
    pytest.param("", "email required", id="empty"),
    pytest.param("invalid", "invalid format", id="missing-at"),
])
def test_validate_email(email: str, expected_error: str | None) -> None:
    if expected_error is None:
        assert validate_email(email) is None
        return

    with pytest.raises(ValidationError, match=expected_error):
        validate_email(email)
```

## Fixtures

- Use fixtures for shared setup that makes tests clearer.
- Use factory fixtures for complex data with per-test variation.
- Avoid autouse fixtures except for global isolation that every test needs.

```python
from typing import Protocol


class UserFactory(Protocol):
    def __call__(self, *, email: str = "user@example.com") -> User: ...


@pytest.fixture
def make_user() -> UserFactory:
    def make(*, email: str = "user@example.com") -> User:
        return User(id="user-1", email=email)
    return make
```

## Mocking

- Mock only system boundaries: network, filesystem, time, randomness, subprocesses, external services.
- Prefer real internal collaborators when cheap.
- Use `spec`, `autospec`, or `create_autospec` when mocking typed collaborators.
- Patch where the object is looked up, not where it is defined.
- Assert calls only when the call is observable behavior or protects an integration contract.

```python
from unittest.mock import patch


def test_process_fetches_payload() -> None:
    with patch("myapp.service.fetch_payload", autospec=True) as fetch:
        fetch.return_value = {"status": "ok"}

        assert process("item-1") == "ok"
        fetch.assert_called_once_with("item-1")
```

Use `pytest-mock` only when the project already has it.

## Async tests

Use the project's async pytest setup. If `pytest-asyncio` sets `asyncio_mode = "auto"`, no marker is needed.

```python
async def test_fetch_user() -> None:
    result = await fetch_user("user-1")
    assert result.user_id == "user-1"
```

## CLI tests

- For Click, use `CliRunner`.
- For argparse-style CLIs, call `main(argv)` and assert exit code plus captured output.
- Use isolated temp directories for filesystem side effects.

```python
def test_command_success(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["process", "input.txt"])
    assert result.exit_code == 0
    assert "processed" in result.output
```

## Property-based tests

Use Hypothesis for parsers, serializers, normalizers, and data transformations with many edge cases. Do not add it for one obvious example case.

```python
@given(st.text(min_size=1, max_size=100))
def test_split_round_trips(text: str) -> None:
    parts = split_message(text)
    assert "".join(parts) == text
```

## Coverage

Coverage is a signal, not the goal. Prefer a lower number backed by meaningful behavior tests over high coverage from trivial tests.
