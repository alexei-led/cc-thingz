---
description:
  Query project history, past decisions, and known gotchas from configured
  memory, local docs, and git history. Use when user asks "last session", "did
  we already", "what did we decide", "project history", "timeline", or "what
  happened with".
name: mem-history
---

# Project History

Use the best available local source. Do not pretend a memory provider exists.

## Scope

Search the current project only. Do not access unrelated repositories or private
paths unless the user explicitly provides them.

See also `learning-patterns` for encoding new observations.

## Source Order

1. Configured project-memory provider, if available.
2. `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `CONTEXT.md`, and `docs/adr/`.
3. `docs/plans/`, completed plans, changelogs, release notes, and issue notes.
4. `git log --oneline --decorate --max-count=20` for recent history.
5. `git log -- <path>` for path-specific history.
6. `git blame <path>` only when line history matters.

## Workflow

1. Scope the question: project-wide, path-specific, or decision-specific.
2. Search local docs with `rg` before broad git history.
3. Query memory only if the runtime has a configured memory provider.
4. Inspect the smallest useful git history.
5. Report facts with file paths, commit hashes, observation IDs, or line references.
6. Label gaps as gaps.

## Commands

```bash
rg -n 'decision|because|ADR|plan|migration|deprecated' AGENTS.md docs . 2>/dev/null
git log --oneline --decorate --max-count=20
git log --oneline -- path/to/file
```

## Output

```markdown
## History

### Findings

- `path:line`, `commit`, or memory ID — fact

### Likely Decision

<grounded explanation>

### Gaps

- <missing evidence>
```
