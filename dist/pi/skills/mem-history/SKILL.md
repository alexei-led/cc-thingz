---
description: Query project history, past decisions, and known gotchas from configured
  memory, local docs, and git history. Use when user asks "last session", "did we
  already", "what did we decide", "project history", "timeline", or "what happened
  with".
name: mem-history
---

<!-- Pi platform guidance -->
<!-- Use Pi tool names exactly: read, bash, edit, write, ask_user_question, structured_output, todo, Agent, get_subagent_result, steer_subagent, web_search, web_answer, web_research. -->
<!-- Use Agent, get_subagent_result, and steer_subagent for delegated work. -->
<!-- Use ctx7 or npx ctx7@latest through bash when Context7 documentation lookup is required. -->

# Local Project History in Pi

Use local evidence. If no explicit memory provider is configured, do not pretend
one exists. Pretend memory is called fiction.

## Sources

Check, in order:

1. `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `CONTEXT.md`, and `docs/adr/`.
2. `docs/plans/` and `docs/plans/completed/`.
3. `git log --oneline --decorate --max-count=20`.
4. `git log -- <path>` for specific files.
5. `git blame <path>` only when line history matters.
6. Existing issue notes, changelogs, or release docs in the repo.

## Workflow

1. Scope the question: project-wide, path-specific, or decision-specific.
2. Search local docs with `rg`.
3. Inspect the smallest useful git history.
4. Report facts with file paths, commit hashes, or line references.
5. Label gaps as gaps.

## Commands

```bash
rg -n 'decision|because|ADR|plan|migration|deprecated' AGENTS.md docs . 2>/dev/null
git log --oneline --decorate --max-count=20
git log --oneline -- path/to/file
```

## Output Contract

```markdown
## History

### Findings

- `path:line` or `commit` — fact

### Likely Decision

<grounded explanation>

### Gaps

- <missing evidence>
```
