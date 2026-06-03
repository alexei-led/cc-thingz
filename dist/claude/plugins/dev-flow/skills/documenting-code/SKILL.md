---
allowed-tools:
- Task
- TaskCreate
- TaskUpdate
- TaskList
- AskUserQuestion
- Read
- Edit
- Write
- Bash(git diff *)
- Bash(git status *)
- Bash(markdownlint-cli2 *)
- Bash(make lint-markdown)
- Bash(make validate)
- Bash(make check)
- Bash(ctx7 *)
- Bash(npx ctx7@latest *)
- Bash(bunx ctx7@latest *)
context: fork
description: Create or update human-facing docs, agent-facing instructions, architecture
  docs, API docs, README content, and useful code comments from implementation facts.
  Use when docs are stale, missing, or must reflect code changes. NOT for code-quality
  review, prompt scoring, speculative docs, or ADRs unless explicitly requested.
name: documenting-code
user-invocable: true
---

# Documentation Update

Scope: documentation files, agent instruction files, and useful code comments
only. Not for code-quality review; use `reviewing-code` for that.

Update docs from implementation facts. Identify the reader first. Apply edits
only when write tools are available. If evidence or validation is missing, report
the gap instead of claiming docs are current.

## Tool use

- Use Read for implementation, tests, and existing docs.
- Use Edit for targeted doc changes. Use Write only for new docs or full rewrites.
- Use Bash only for status, diffs, markdown lint, docs checks, and narrow repo validation.
- Use TaskCreate only for a large documentation audit that needs a bounded read-only mapping pass. Verify the returned claims before editing.
- Use AskUserQuestion only when scope or reader is ambiguous.

## Reader model

Human reader:

- Short, structured, readable, and useful.
- Start with what the reader can do after reading.
- Use examples close to the concept.
- Use Mermaid diagrams only for non-trivial structure, flow, lifecycle,
  ownership, or trade-offs.
- Match existing docs style; do not invent custom fonts, colors, or visual design.

Agent reader:

- Concise operational instructions for LLMs.
- Use headers, bullets, numbered steps, and exact output contracts.
- Remove fluff, duplicate rules, generic knowledge, tables, diagrams, and visual polish.
- Route scoring or quality review of instructions to `reviewing-instructions`.

Code reader:

- Comments/docstrings explain contracts, constraints, invariants, side effects,
  errors, or non-obvious choices.
- Delete comments that restate code.
- Avoid comments in tests unless they explain an essential external behavior or edge case.

## Workflow

1. Determine scope from the user request or changed files. Do not ask if clear.
2. Read relevant code, tests, and existing docs.
3. Choose reader type: human, agent, code, or mixed.
4. Compare docs to current behavior. Code wins unless the user says docs are the contract.
5. Update the smallest useful docs.
6. Verify docs and runnable examples when practical.
7. Report changed files, checks, and remaining issues.

For large audits only, spawn one bounded read-only subagent with a narrow brief:
map changed behavior, existing docs, stale sections, and missing docs. Require
file paths and line evidence. Do not let the subagent edit.

## What to update

- README usage, setup, quick start, and release notes for user-visible changes.
- API docs for parameter, output, error, side effect, or example changes.
- Architecture docs for boundary, data-flow, ownership, deployment, or major trade-off changes.
- Agent docs for skills, agents, hooks, commands, tools, routing, and operating rules.
- Generated catalogs only through source files and generator scripts.
- Code comments only when they add useful contract or reasoning value.

## Verification

Prefer the narrowest relevant checks:

```bash
git diff --stat
markdownlint-cli2 '**/*.md'
make lint-markdown
make validate
```

Run documented commands or examples when practical. If a check cannot run, state why.

## Output

```markdown
## Documentation Update

Updated:

- `path` — <what changed and reader served>

Verified:

- <check>: passed | skipped (<reason>)

Issues: none | <remaining issue>
```

## Reviewer output

Read-only role only. Apply nothing and run nothing.

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
- No recent changes: ask what to document instead of inventing docs.
- Generated doc target: edit source and rebuild, not generated output.
- Docs/code conflict: report it; update docs to code unless user says docs are intended contract.
- Verification failure: quote the exact failure and do not claim success.
