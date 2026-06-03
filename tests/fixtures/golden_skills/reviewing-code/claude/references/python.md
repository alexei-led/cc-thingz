# Python Review Reference

Host skill owns scope, severity, scoring, and output. This file adds Python-specific evidence gathering and checks.

## Tool-enabled review

Run configured project tools only when the active role can execute commands. Prefer project commands when present.

Useful Python gates:

```bash
ruff check .
pyright .
pytest --tb=short
bandit -r .
```

Treat tool output as evidence, then map it through the severity rubric. If a tool is missing or not configured, report the gap and continue source review. Do not install tools.

## Read-only review

When commands are unavailable, use supplied diff, file reads, and caller-supplied output. Follow imports and direct callers for changed public functions, CLI commands, routes, async boundaries, and persistence code.

## Focus checks

Correctness:

- `None` handling at optional inputs and lookup results.
- Mutable defaults or shared mutable module state.
- Broad exception handling that hides failures or loses cause.
- Type hints that do not match runtime shape at boundaries.
- Off-by-one ranges, slicing, pagination, and timezone handling.

Security:

- SQL injection from string-built queries.
- Command injection via shell execution or unsafe argument construction.
- Unsafe deserialization, dynamic import, `eval`, or `exec` on untrusted input.
- Path traversal from user-controlled paths.
- Weak crypto, weak token generation, or secrets in logs/errors/config.
- Missing authorization at concrete route, command, or service boundary.

Reliability:

- Blocking I/O in async code.
- Missing timeout, cancellation, or cleanup for network and subprocess calls.
- Unclosed files, responses, sessions, cursors, or temporary resources.
- Global caches or background tasks without bounds or shutdown.

Performance:

- N+1 database or API calls.
- Quadratic loops on realistic input sizes.
- Repeated expensive parsing, compiling, or filesystem work in hot paths.
- Unbounded memory growth from caches, list materialization, or retained objects.

Tests:

- Changed business behavior without success, failure, and edge tests.
- Bug fixes without a regression test at the public seam.
- Over-mocked tests that skip the route, CLI, or service contract.

## Version-gated checks

Inspect `pyproject.toml`, `.python-version`, lockfiles, and CI before applying version-specific claims.

- Python 3.14 free-threading and subinterpreters matter only when the project opts in or the code explicitly targets them.
- Do not recommend version-specific syntax or APIs unless the project supports them.

## Failure handling

- Test, typecheck, or lint failure in reviewed scope: map severity by impact; build/test blockers are Critical.
- Ambiguous security risk: use Needs review and name the missing trust boundary or configuration.
- No validation library: do not flag every boundary. Flag only concrete unvalidated external input that reaches sensitive behavior.
- LSP or graph unavailable: note reduced cross-file coverage only if it affects the finding.
