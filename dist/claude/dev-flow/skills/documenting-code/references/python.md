# Python Documentation

Use this only for Python files. The host skill owns scope, editing, and verification.

## Public API docs

- Public modules, classes, functions, and methods need docstrings when behavior is not obvious from name and types.
- Type hints carry type information; do not repeat obvious types in prose.
- Document behavior, parameters with constraints, return values, raised exceptions,
  side effects, invariants, and examples for non-trivial APIs.
- Follow the style already used by the project. If no style exists, use concise Google-style docstrings.

Good:

```python
def charge_customer(customer_id: str, amount_cents: int) -> str:
    """Charge the default payment method.

    Raises:
        PaymentDeclined: The processor rejected the charge.
        NetworkError: The processor could not be reached.
    """
```

Avoid docstrings that restate the function name or type hints.

## Comments

Keep comments that explain:

- business rules or invariants
- external service limits
- compatibility workarounds
- why a simple-looking alternative is wrong

Delete comments that paraphrase Python syntax or nearby code.

## Tests

Tests should be readable through names, fixtures, and assertions. Avoid comments
unless they explain non-obvious external behavior or why an edge case matters.

## README and examples

- Install and run commands must match current packaging and tooling.
- Examples should import current modules and work with current signatures.
- If examples cannot run because dependencies are unavailable, state that.

## Checks

Prefer configured project checks. If available, use narrow docs checks:

```bash
pydoc <module>
sphinx-build -b html docs/ docs/_build/
pytest <relevant tests>
```

If imports fail, report the failure and continue with manual docstring inspection.
