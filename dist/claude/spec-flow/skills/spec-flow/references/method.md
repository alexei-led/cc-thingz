# Spec-flow method

Create only the artifacts the work needs, not ceremony because the folders exist.

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

Ask only what blocks a useful plan, at most 3-5 questions: the user-visible
outcome, what is out of scope, what must stay unchanged, which data, API, or
permission boundary matters, and how to verify success. For deep product
discovery, keep notes in a `REQ-*` and plan later.

## Validation expectations

`specctl validate` is intentionally stricter than a TODO list. A task should fail validation until it has meaningful Description, Acceptance, and Files sections. This keeps `spec-flow` from starting vague work.

Draft tasks from `scripts/specctl new task` are allowed to be invalid until the planning step fills them in.

## Definition of ready

A task is ready when:

- status is `todo`
- every `blocked-by` task is `done`
- validation passes
- no active session blocks switching
