---
allowed-tools:
- AskUserQuestion
- Agent
- Read
- Write
- Edit
- Glob
- Grep
- mcp__morphllm__edit_file
- Bash(scripts/specctl *)
- Bash(rg *)
- Bash(fd *)
- Bash(date *)
- Bash(mkdir *)
argument-hint: '[REQ-id | EPIC-id | "idea"]'
context: fork
description: Turn a requirement or a concrete feature idea into an EPIC with vertical-slice
  TASKs. Use when you have a REQ file, or a feature idea already specific enough for
  a quick 3–5 question pass, and need an executable plan with dependencies and acceptance
  criteria. NOT for open-ended idea exploration — use brainstorming-ideas. NOT for
  capturing PRD-quality requirements — use spec-interview. NOT for implementing tasks
  — use spec-work.
model: sonnet
name: spec-plan
user-invocable: true
---

# `spec plan` — create an epic with vertical-slice tasks

CLI at `scripts/specctl`. Turn a requirement (or idea) into an `EPIC-*.md` + a set of independently grabbable `TASK-*.md` files with dependencies, blockers, and acceptance criteria.

Role: technical planner. Goal: epic + tasks. Out of scope: implementation code.

## Input

The user's input is one of:

- `REQ-id` — read requirement, create epic + tasks
- `EPIC-id` — refine existing epic
- `"<idea text>"` — only when the idea is already concrete: ask 3–5 quick
  questions, then plan. For open-ended or unvalidated ideas, use the
  `brainstorming-ideas` skill first; for deep PRD-quality requirements, use the
  `spec-interview` skill instead.

If empty, ask: "What should I plan? Give me a REQ id or describe the feature."

## Step 0: Setup

```bash
scripts/specctl init 2>/dev/null || true
mkdir -p .spec/epics .spec/tasks
```

## Step 1: Load context

- **REQ id** → `scripts/specctl show REQ-<id>` and read the file.
  - If REQ-id not found: tell the user "REQ-<id> does not exist. Run `spec-status` to list requirements." Stop.
- **EPIC id** → `scripts/specctl show EPIC-<id>` — refinement; may add/update tasks.
  - If the epic already has in-progress or done tasks, warn: "EPIC-<id> has tasks in progress. Adding tasks may create dependency conflicts. Proceed?" Require explicit confirmation.
- **Idea text** → ask 3–5 quick questions.

## Step 2: Research (optional)

Ask the user a multi-choice question: "Should I explore the codebase first?"

- Yes, quick scan — find patterns and conventions
- No, I know the codebase — skip

If yes, delegate codebase exploration to a research/exploration agent if the runtime supports it. The prompt: "Find existing patterns, conventions, and code relevant to <requirement summary>. Look for similar implementations, reusable code, and architectural patterns."

Capture from the research:

- File paths + line refs
- Existing patterns to follow
- Code to reuse
- Architectural conventions

## Step 3: Create the plan

Build vertical-slice tasks: each is a tracer bullet (narrow but complete path through the system), M-sized (3–5 files / 3–5 criteria) is the target, ordering via `blocked-by`, tests in the same slice as the behavior. For the full vertical-slice rules, task sizing, dependency rules, and the pre-write mental-model checklist, read `references/planning-rules.md`.

## Step 4: Present plan for approval

Before writing files, show the plan:

```
## Proposed plan for <requirement>

### Epic: EPIC-<slug>
<overview>

### Tasks (in order):

1. TASK-<slug>-1: <title>
   - Size: M
   - Files: <expected files>
   - Blocked by: none
   - Open questions: none | <specific blocker>
   - Verifiable: <demo/check/test>

2. TASK-<slug>-2: <title>
   - Size: M
   - Files: <expected files>
   - Blocked by: TASK-<slug>-1
   - Verifiable: <demo/check/test>
```

Ask multi-choice: "Does this plan look right?"

- Yes, create files
- Needs changes (user explains)
- Too detailed — simplify
- Not detailed enough — add more tasks

Wait for approval before writing.

## Step 5: Write files

### Epic file

```markdown
---
id: EPIC-<slug>
status: open
priority: <from REQ or normal>
implements: REQ-<slug>
created: <date>
tasks:
  - TASK-<slug>-1
  - TASK-<slug>-2
---

# <Title>

## Overview

<What this epic accomplishes>

## Approach

<High-level technical approach. Reference existing patterns: "Follow pattern at src/auth.ts:42".>

## Quick commands

\`\`\`bash
make build
make test
make lint
\`\`\`

## Acceptance

- [ ] All REQ criteria met
- [ ] Tests pass
- [ ] No lint errors

## References

- Requirement: REQ-<slug>
- <Other refs from research>
```

### Task files

For each task:

```markdown
---
id: TASK-<slug>-N
status: todo
priority: normal
epic: EPIC-<slug>
blocked-by: [TASK-<slug>-X] # or []
size: M
---

# <Task title>

## Description

<What to build — WHAT, not HOW. Describe the end-to-end behavior this vertical slice delivers.>

## Notes

- Blockers or open questions: <none | specific human decision / access / manual check needed>
- Out of scope: <adjacent behavior not included>

## Files

- `path/to/file.ts` — <what changes>

## Approach

<High-level approach. Reference patterns: "Follow pattern at src/example.ts:15".>

## Acceptance

- [ ] <observable criterion 1>
- [ ] <observable criterion 2>
- [ ] Success-path test exists if code behavior changed
- [ ] Error or edge-case test exists when relevant
- [ ] Tests pass
```

## Step 6: Validate & complete

```bash
scripts/specctl validate
scripts/specctl status
```

Show summary:

```
Created:
- EPIC-<slug> with <N> tasks
- Tasks: TASK-<slug>-1, TASK-<slug>-2, ...

Next steps:
1. Start work: use the `spec-work` skill — `spec-work EPIC-<slug>`
2. Review plan: read .spec/epics/EPIC-<slug>.md
```

## Golden rule: no implementation code

Plans describe WHAT, not HOW.

- **Allowed**: signatures, interfaces, pattern references with `file:line`, API notes from docs.
- **Forbidden**: complete function implementations, copy-paste-ready code blocks (>10 lines), "here's what you'll write" snippets.

Implementation happens in the `spec-work` skill.
