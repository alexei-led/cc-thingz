---
description: Idiomatic Python 3.12+ development. Use when writing Python code, CLI
  tools, scripts, or services. Emphasizes stdlib, type hints, fast pytest feedback,
  uv/ruff/pyright toolchain, and minimal dependencies. NOT for Go, TypeScript, or
  shell-only tasks.
name: writing-python
---

# Python Development

Use this only for Python 3.12+ code. Keep language-agnostic rules out of this skill.

## Read First

Read [principles.md](references/principles.md) before generating or changing Python code.

## Core Rules

- Prefer existing project patterns over these defaults.
- Inspect the project Python target before using 3.12-only syntax.
- Prefer stdlib and existing dependencies before adding packages.
- Validate untyped boundary input before it spreads.

## Conditional References

- [patterns.md](references/patterns.md) — read for module design, typing, async, config, file I/O, and error patterns.
- [cli.md](references/cli.md) — read before writing or changing Python CLIs.
- [testing.md](references/testing.md) — read before adding or reshaping Python tests; treat slow tests as feedback-loop defects.

## Verification

Run project-configured tests, lint, format, and type checks. Prefer focused pytest commands for the edit loop, then the broader project command before final output. Prefer pytest, ruff, and pyright when present.

If a tool is not configured, say so and run the closest available gate. If a check fails, diagnose the cause, make a targeted fix, and rerun the relevant check.

## Python-Specific Failure Cases

- No clear project root: locate `pyproject.toml` before editing or choosing commands.
- Unknown Python target: inspect `pyproject.toml`, `.python-version`, CI, or lockfiles before using 3.12-only syntax.
- Type checker reports missing attributes: check imports, package exports, and runtime shape before loosening types.

## Final Response

Include:

- changed files
- checks run and results
- checks skipped with reasons
- remaining risks or follow-ups
