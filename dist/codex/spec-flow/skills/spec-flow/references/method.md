# Spec-flow method

## Artifact choice

Use the smallest artifact set that keeps work safe:

- one obvious change → one `TASK-*`
- related multi-step change → one `EPIC-*` with several `TASK-*`
- unclear product intent → one `REQ-*`, then plan tasks later

Do not create ceremony just because the folders exist.

## Artifact quality

A good task has:

- one vertical slice
- observable acceptance criteria
- a verification command or manual check
- clear blockers via `blocked-by`
- meaningful file/scope notes, even if the exact file is still a likely path
- out-of-scope notes when nearby work is tempting

Avoid:

- vague tasks like "improve auth"
- layer-only tasks like "add database schema" unless independently useful
- placeholder acceptance like "it works"
- hidden dependencies not listed in `blocked-by`
- file scope that says only `TBD`

## Minimal task template

```markdown
---
id: TASK-<slug>
status: todo
priority: normal
blocked-by: []
---

# <Task title>

## Description

<one vertical slice>

## Acceptance

- [ ] <observable behavior>
- [ ] <verification command or manual check>

## Files

- `path/or/TBD` — <expected change>

## Out of scope

- <excluded adjacent work>
```

## Planning output

Show this before writing files:

```markdown
## Proposed plan

Scope: <idea or REQ>
Artifact set: <TASK only | EPIC + TASKs | REQ + EPIC + TASKs>

### Tasks

1. TASK-<slug> — <title>
   - Why: <one line>
   - Blocked by: [] | [TASK-x]
   - Acceptance: <2-4 observable checks>
   - Verification: <command/manual check>

### Open questions

- none | <specific blocker>
```

## Mini-interview

Ask only what blocks a useful plan. Prefer 3-5 questions.

Good questions:

- What user-visible outcome should this slice deliver?
- What is explicitly out of scope?
- What existing behavior must stay unchanged?
- What data, API, or permission boundary matters?
- How should we verify success?

If the user needs deep product discovery, keep notes in a `REQ-*` first and plan later.

## Validation expectations

`specctl validate` is intentionally stricter than a TODO list. A task should fail validation until it has meaningful Description, Acceptance, and Files sections. This keeps `spec-flow` from starting vague work.

Draft tasks from `scripts/specctl new task` are allowed to be invalid until the planning step fills them in.

## Definition of ready

A task is ready when:

- status is `todo`
- every `blocked-by` task is `done`
- validation passes
- no active session blocks switching

## Definition of done

A task is done when:

- acceptance criteria were checked
- verification evidence is recorded in `--tests`
- changed files or `none` are recorded
- follow-up work is separate
- the active session is cleared by `specctl done`

## Execution checklist

Before edits:

- active session checked
- task context read
- blockers resolved
- short implementation plan approved

Before done:

- scoped diff reviewed or offered
- acceptance criteria checked
- tests/lint/build/manual check recorded
- follow-up work captured separately
