# Python Testing Reference

## Test Design

- Test behavior through public interfaces, not private helpers.
- Prefer integration-style tests when they give a stable signal.
- Mock only system boundaries: external APIs, time, randomness, filesystem, subprocesses.
- Do not mock internal collaborators just to assert call counts.
- Use red-green-refactor for risky changes: one failing test, minimal code, refactor only when green.
- Delete shallow tests once deeper interface tests cover the behavior.

## Framework: pytest

```bash
uv add --group dev pytest pytest-asyncio pytest-cov pytest-timeout hypothesis
pytest -v                    # unit tests
pytest -m integration        # integration tests
pytest -m "not integration"  # skip slow tests
```

## Pytest Configuration

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = ["--import-mode=importlib", "--strict-markers", "-ra"]
asyncio_mode = "auto"
markers = [
    "integration: tests using real filesystem or external processes",
    "e2e: end-to-end tests (slow, local only)",
]

[tool.coverage.run]
source = ["my_package"]
branch = true
exclude_lines = ["pragma: no cover", "if __name__ == .__main__.", "logger\\."]
```

## Tiered Testing

| Tier        | Scope                     | Command                 | Speed  |
| ----------- | ------------------------- | ----------------------- | ------ |
| Unit        | Mocked, isolated          | `make test`             | Fast   |
| Integration | Real filesystem/processes | `make test-integration` | Medium |
| E2E         | Full system               | `make test-e2e`         | Slow   |

## Basic Tests

```python
def test_validate_email_valid():
    assert validate_email("user@example.com") is None

def test_validate_email_empty():
    with pytest.raises(ValidationError, match="email required"):
        validate_email("")
```

## Parametrized Tests

```python
@pytest.mark.parametrize("email,expected_error", [
    pytest.param("user@example.com", None, id="valid-email"),
    pytest.param("", "email required", id="empty-string"),
    pytest.param("invalid", "invalid format", id="no-at-sign"),
    pytest.param("user@", "invalid format", id="no-domain"),
])
def test_validate_email(email: str, expected_error: str | None):
    if expected_error:
        with pytest.raises(ValidationError, match=expected_error):
            validate_email(email)
    else:
        assert validate_email(email) is None
```

## Fixtures

```python
@pytest.fixture
def user_service(mock_repo):
    return UserService(repo=mock_repo)

@pytest.fixture
def mock_repo():
    return Mock(spec=UserRepository)

def test_get_user(user_service, mock_repo):
    mock_repo.get.return_value = User(id="123", name="Test")
    result = user_service.get_user("123")
    assert result.name == "Test"
    mock_repo.get.assert_called_once_with("123")
```

### Factory Fixtures

For complex test data, use factory fixtures that return builder functions:

```python
@pytest.fixture
def make_mock_provider():
    """Factory: build a mock provider with configurable status."""
    def _make(*, has_status: bool = False, interactive: bool = False):
        provider = MagicMock(spec=AgentProvider)
        if has_status:
            status = StatusUpdate(raw_text="Working...", display_label="…working")
            provider.parse_terminal_status.return_value = status
        else:
            provider.parse_terminal_status.return_value = None
        return provider
    return _make

@pytest.fixture
def make_jsonl_entry():
    """Factory: build raw JSONL dict."""
    def _make(msg_type="assistant", content="", *, timestamp=None):
        return {"type": msg_type, "message": {"content": content},
                "timestamp": timestamp or "2024-01-01T00:00:00Z"}
    return _make
```

### Autouse Fixtures for Environment

```python
# tests/conftest.py — root conftest: force env BEFORE imports
import os, tempfile
os.environ["API_TOKEN"] = "test-token"
os.environ["CONFIG_DIR"] = tempfile.mkdtemp(prefix="test-")

@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Remove provider-specific env vars so tests use defaults."""
    for key in list(os.environ):
        if key.startswith("MYAPP_") and key.endswith("_COMMAND"):
            monkeypatch.delenv(key)
```

## Mocking

**Use `unittest.mock` + `pytest-mock` (mocker fixture) for all mocking.**

```python
from unittest.mock import Mock, MagicMock, AsyncMock, patch, create_autospec
```

### Mock Types

| Type                   | Use When                                                     |
| ---------------------- | ------------------------------------------------------------ |
| `Mock()`               | Basic mock, no magic methods                                 |
| `MagicMock()`          | Needs magic methods (`__len__`, `__iter__`, context manager) |
| `AsyncMock()`          | Async functions (`async def`)                                |
| `create_autospec(cls)` | Type-safe mock that validates signatures                     |

### Argument Matching (CRITICAL)

| Approach                | Use When                                          |
| ----------------------- | ------------------------------------------------- |
| Exact value             | Business-critical values (IDs, table names, keys) |
| `call_args` inspection  | Checking specific args without full match         |
| Custom `__eq__` matcher | Partial object matching                           |

```python
def test_with_exact_values():
    mock_repo = Mock()
    service = Service(repo=mock_repo)
    service.process_order("order-123", "customer-456")
    mock_repo.save.assert_called_once_with("order-123", "customer-456")

def test_with_partial_matching():
    mock_repo = Mock()
    service = Service(repo=mock_repo)
    service.create_user(email="test@example.com")
    call_args = mock_repo.save.call_args
    assert call_args.kwargs["email"] == "test@example.com"
    assert call_args.kwargs["id"] is not None
```

### Patching Best Practices

**Patch where the object is looked up, not where it's defined:**

```python
# myapp/services.py
from myapp.clients import api_client

# tests/test_services.py
@patch("myapp.services.api_client")  # patch where USED
def test_process(mock_client):
    mock_client.fetch.return_value = {"data": "test"}
    assert process() == {"data": "test"}

# With pytest-mock (preferred)
def test_process(mocker):
    mock_client = mocker.patch("myapp.services.api_client")
    mock_client.fetch.return_value = {"data": "test"}
    assert process() == {"data": "test"}
```

### Async Mocking

```python
async def test_async_service():
    mock_client = AsyncMock()
    mock_client.fetch.return_value = {"status": "ok"}
    service = Service(client=mock_client)
    result = await service.process()
    assert result == "ok"
    mock_client.fetch.assert_awaited_once()
```

## Property-Based Testing (Hypothesis)

Use Hypothesis for edge case discovery, especially for parsing, serialization, and data transformation:

```python
from hypothesis import given, strategies as st

@given(st.text(min_size=1, max_size=100))
def test_message_splits_correctly(text):
    result = split_message(text)
    assert all(len(msg) <= 4096 for msg in result)
    assert "".join(result) == text

@given(st.integers(min_value=0, max_value=1000))
def test_rate_limit_non_negative(value):
    result = compute_delay(value)
    assert result >= 0
```

## Click CLI Testing

```python
from click.testing import CliRunner

@pytest.fixture
def runner():
    return CliRunner()

def test_command_success(runner):
    result = runner.invoke(cli, ["subcommand", "--flag", "value"])
    assert result.exit_code == 0
    assert "expected output" in result.output

def test_command_with_env(runner):
    result = runner.invoke(cli, [], env={"MY_VAR": "value"})
    assert result.exit_code == 0

def test_command_file_input(runner):
    with runner.isolated_filesystem():
        Path("input.txt").write_text("test data")
        result = runner.invoke(cli, ["process", "input.txt"])
        assert result.exit_code == 0
```

## Async Tests

```python
# With asyncio_mode = "auto", no @pytest.mark.asyncio needed
async def test_async_fetch():
    result = await fetch_data("https://api.example.com")
    assert result is not None

@pytest.fixture
async def async_client():
    client = AsyncClient()
    yield client
    await client.close()
```

## Test Organization

```
tests/
├── conftest.py              # Root: env vars, shared fixtures
├── my_package/
│   ├── conftest.py          # Unit fixtures, factory fixtures
│   ├── test_config.py
│   ├── test_session.py
│   └── handlers/
│       └── test_text_handler.py
├── integration/
│   ├── conftest.py          # Real resources, cleanup
│   └── test_full_flow.py
└── e2e/
    └── test_system.py
```

## Integration Tests

```python
@pytest.mark.integration
async def test_session_lifecycle(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    manager = SessionManager(config_dir)

    session_id = manager.create_session("test-window")
    assert manager.get_session(session_id) is not None

    manager.close_session(session_id)
    assert manager.get_session(session_id) is None
```

## Coverage

```bash
pytest --cov=src --cov-report=html
pytest --cov=src --cov-fail-under=80
```

## Guidelines

**CRITICAL: Zero tolerance for test waste**

- **No pointless tests**: Don't test trivial behavior (getters, constructors)
- **No naive tests**: Include edge cases, not just happy paths
- **No duplicate tests**: Same scenario tested multiple ways → keep one
- **Combine with parametrize**: 2+ tests for same function → `@pytest.mark.parametrize` (mandatory)
- **Use `pytest.param(..., id="desc")`** for readable parametrized test names
- **No comments in tests**: Tests should be self-explanatory

**Standard Guidelines**

- One assertion per test (when practical)
- Descriptive test names: `test_validate_email_empty_raises_error`
- Use fixtures for setup, factory fixtures for complex data
- Keep tests independent
- Test behavior, not implementation
- Use `spec=` or `create_autospec` for type-safe mocks
