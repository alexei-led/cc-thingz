---
description: Idiomatic Python 3.12+ development. Use when writing Python code, CLI
  tools, scripts, or services. Emphasizes stdlib, type hints, uv/ruff/pyright toolchain,
  and minimal dependencies. NOT for Go, TypeScript, or shell-only tasks.
name: writing-python
---

<!-- Pi platform guidance -->
<!-- Use Pi tool names exactly: read, bash, edit, write, ask_user_question, structured_output, todo, Agent, get_subagent_result, steer_subagent, web_search, web_answer, web_research. -->
<!-- Use Agent, get_subagent_result, and steer_subagent for delegated work. -->
<!-- Use ctx7 or npx ctx7@latest through bash when Context7 documentation lookup is required. -->

# Python Development

Use this only for Python 3.12+ code. Keep language-agnostic rules out of this skill.

## Read First

Read [principles.md](references/principles.md) before generating or changing Python code.

## Core Rules

- Prefer existing project patterns over these defaults.
- Use stdlib first for small tools.
- Use concrete types; validate untyped boundary input before it spreads.
- Use Python 3.12 typing syntax when the project target allows it.
- Use guard clauses for validation and parsing.

## Conditional References

- [patterns.md](references/patterns.md) — read for module design, typing, async, config, file I/O, and error patterns.
- [cli.md](references/cli.md) — read before writing or changing Python CLIs.
- [testing.md](references/testing.md) — read before adding or reshaping Python tests.

## Verification

Run project-configured tests, lint, format, and type checks. Prefer pytest, ruff, and pyright when present.

If a tool is not configured, say so and run the closest available gate. If a check fails, diagnose the cause, make a targeted fix, and rerun the relevant check.

## Python-Specific Failure Cases

- No clear project root: locate the `pyproject.toml` before editing or choosing commands.
- Unknown Python target: inspect `pyproject.toml`, `.python-version`, CI, or lockfiles before using 3.12-only syntax.
- Type checker reports missing attributes: check imports, package exports, and runtime shape before loosening types.
