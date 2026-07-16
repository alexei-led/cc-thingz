---
description: Create or update human-facing docs, agent-facing instructions, architecture
  docs, API docs, README content, and useful code comments from implementation facts.
  Use when docs are stale, missing, or must reflect code changes. NOT for code-quality
  review, prompt scoring, speculative docs, or ADRs unless explicitly requested.
name: documenting-code
---

# Documenting Code

Update only useful documentation. Start from code facts, identify the reader, and
make the smallest doc change that helps that reader act correctly.

## Role-gated action

Detect capability from tools, not prose:

- Write-capable role: edit docs and run validation.
- Read-only role: apply nothing; emit proposed edits in the output contract.

## Reader model

Choose the reader before writing.

Human reader:

- Make docs scannable: clear title, short overview, focused sections, examples.
- Keep docs short. Link to detail instead of creating long reads.
- Use Mermaid diagrams only when they answer a real structure, flow, lifecycle,
  ownership, or trade-off question.
- Match the existing docs style. Do not invent fonts, colors, or custom visual
  treatment unless the docs system already supports it.

Agent reader:

- Write terse operational instructions for LLMs.
- Prefer headers, bullets, numbered steps, and exact contracts.
- Remove generic knowledge, duplicate rules, pretty formatting, diagrams, tables,
  long rationale, and advice the model already knows.
- If the task is to review or score agent instructions, use `reviewing-instructions`.

Code reader:

- Comments and docstrings explain contracts, constraints, invariants, side
  effects, error behavior, and non-obvious decisions.
- Delete comments that paraphrase code.
- Avoid comments in tests unless they explain non-obvious external behavior or
  why an edge case matters.

## Language references

Load only references matching changed implementation files:

- C# /.NET: `references/csharp.md`
- Go: `references/go.md`
- Java/Kotlin: `references/java-kotlin.md`
- Python: `references/python.md`
- Rust: `references/rust.md`
- TypeScript: `references/typescript.md`
- Web: `references/web.md`

Mixed languages: load each matching reference. Unknown language: use this file
only.

## Workflow

1. Identify scope from the user request or changed files. Do not ask if scope is clear.
2. Read relevant implementation, tests, and existing docs before writing.
3. Decide reader type: human, agent, code reader, or mixed.
4. Check docs against current behavior. Code wins unless the user says docs define the intended contract.
5. Use `looking-up-docs` only when external API syntax or behavior is uncertain.
6. Use one bounded read-only subagent only for large doc audits; verify its claims before editing.
7. Update the smallest useful docs. Do not create speculative docs.
8. Verify with the narrowest docs or repo checks available.

## What to update

- README usage, setup, or quick start when user-visible behavior changes.
- API docs when parameters, outputs, errors, side effects, or examples change.
- Architecture docs when boundaries, data flow, ownership, deployment units, or
  major trade-offs change.
- Agent instructions when skills, agents, hooks, commands, tools, routing, or
  operating rules change.
- Generated catalogs only through their source files and generator scripts.
- Code comments/docstrings only when they add useful contract or reasoning value.

## Rules

- No promotional filler.
- No dead, future, or speculative behavior.
- No ADRs or `docs/adr/` changes unless explicitly requested.
- Keep private paths, secrets, tokens, and internal credentials out of docs.
- Prefer runnable examples. If an example cannot be run, state why.
- For human docs, favor a compact diagram over paragraphs only when the diagram
  improves understanding.
- For agent docs, optimize for token efficiency over visual appeal.

## Verification

Run the narrowest relevant checks, for example:

```bash
markdownlint-cli2 '**/*.md'
make lint-markdown
make validate
```

Also run documented commands or examples when practical. If a check is missing or
not practical, state the reason and run the closest available check.

## Output

Write-capable role:

```markdown
## Documentation Update

Updated:

- `path` — <what changed and reader served>

Verified:

- <check>: passed | skipped (<reason>)

Issues: none | <remaining issue>
```

Read-only role:

```markdown
## Proposed Changes

### Change 1: <brief description>

File: `path/to/doc`
Action: CREATE | MODIFY | DELETE
Reader: human | agent | code

Code:
<doc content or patch-sized replacement with enough context>

Rationale: <code fact that makes this stale or missing>
```

## Failure handling

- Ambiguous scope: ask one scoped question.
- Missing changed-file context: inspect `git diff --name-only`; if unavailable,
  ask for paths.
- No stale docs found: say so and report what was checked.
- Docs/code conflict: report the conflict; update docs to code unless user says docs are intended contract.
- Validation failure: report the exact failure and do not claim docs are current.