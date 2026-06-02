---
description: Spec-driven development status and orientation. Use when checking overall
  project state, viewing a specific task with its linked req/epic, listing tasks by
  status, running a quality audit for orphans/cycles/missing fields, or for a pipeline
  overview when unsure which spec sub-skill to use. NOT for mutating state — read-only;
  use spec-done or spec-work for state changes.
name: spec-status
---

# spec — status and orientation

Read-only entry point for spec-driven development: report progress, or orient the user to the right sub-skill.

If `.spec/` doesn't exist, tell the user: "No `.spec/` folder. Use the `spec-init` skill to initialize the project." and stop.

```bash
scripts/specctl status 2>/dev/null || echo "NO_SPEC"
```

## Pipeline

`spec-init` → `spec-interview` → `spec-plan` → `spec-work` → `spec-done` (loop until epic complete)

`spec-status` reads state at any point.

### Sub-skills

- `spec-init` — initialize `.spec/`, or add requirements from an existing doc
- `spec-interview` — deep PRD-quality requirement capture via Q&A
- `spec-plan` — create an EPIC + vertical-slice TASKs from a requirement or idea
- `spec-new` — one-off task or requirement from a template
- `spec-work` — implement the next ready task (one per session, user approval at every step)
- `spec-done` — mark a task complete with evidence; optionally discover or verify first
- `spec-status` — overview, single-task detail, filtered list, or quality audit

### Where to start

- No `.spec/` yet → use the `spec-init` skill to initialize the project
- Have an idea → use the `spec-interview` skill to capture requirements
- Have REQ files → use the `spec-plan` skill to create tasks
- Have TASK files → use the `spec-work` skill to implement the next task

### File structure

- `.spec/reqs/REQ-*.md` — requirements (WHAT / WHY)
- `.spec/epics/EPIC-*.md` — epics grouping related tasks
- `.spec/tasks/TASK-*.md` — vertical-slice tasks with dependencies
- `.spec/memory/` — pitfalls, conventions, decisions discovered during work
- `.spec/SESSION.yaml` — current session (task, step, base commit)
- `.spec/PROGRESS.md` — activity log

### Principles

- REQ = WHAT / WHY (business requirements, success criteria)
- TASK = vertical slice with acceptance criteria
- Blockers and open questions stay in artifact frontmatter or body
- One task per session — complete before starting the next
- Quality gates: build, test, lint — every time
- User approves every edit — no hidden automation

For the bundled `specctl` CLI command reference, read `references/specctl-commands.md`.

## Status views

CLI at `scripts/specctl`. Match the user's request to one of these views:

- **Overview** — "what's the status", "show progress", no specific task named.
- **Specific task** — user names a `TASK-id`; show the task + its linked req/epic.
- **Filtered list** — user wants all tasks, just todo, or just completed.
- **Quality audit** — user wants to know about orphans, cycles, stale tasks, missing fields.

## Overview

```bash
total=$(fd -e md . .spec/tasks/ | wc -l | tr -d ' ')
done=$(rg -l '^status: done' .spec/tasks/ 2>/dev/null | wc -l | tr -d ' ')
branch=$(git branch --show-current 2>/dev/null || echo "no-git")
```

Pick the next priority-ordered todo task:

```bash
next=$(rg -l '^priority: critical' .spec/tasks/ 2>/dev/null | xargs rg -l '^status: todo' 2>/dev/null | head -1)
[ -z "$next" ] && next=$(rg -l '^priority: normal' .spec/tasks/ 2>/dev/null | xargs rg -l '^status: todo' 2>/dev/null | head -1)
[ -z "$next" ] && next=$(rg -l '^status: todo' .spec/tasks/ 2>/dev/null | head -1)
```

Build a top-5 requirement rollup (tasks per REQ, with done counts).

Show:

```
## Spec status

Branch: <branch>
Tasks: <done>/<total> complete
Next ready: <task id or "none">

### Top requirements
- REQ-<slug>: <m>/<n> tasks done
- ...

### Suggested next
spec-work          # pick up the next ready task
spec-status list   # see every task
spec-status check  # quality audit
```

## Specific task

User passed a `TASK-id`. If no matching file exists under `.spec/tasks/`, say "Task not found." and stop.

Read the task file and any linked epic / requirement.

Show:

```
## TASK-<id>

Status: <status>
Priority: <priority>
Epic: <epic id or none>
Blocked by: <deps>

<task body>

### Epic
<epic overview>

### Requirement
<linked REQ summary>
```

## Filtered list

- `list` — every task
- `todo` — only `status: todo`
- `completed` — only `status: done`

Group by epic; show priority and a one-line summary per task.

## Quality audit

```bash
scripts/specctl validate
scripts/specctl status
```

Surface:

- Orphan tasks (no epic, no requirement link)
- Dependency cycles
- Tasks missing `acceptance` criteria
- Stale tasks (`status: in-progress` with no recent commits)
- Requirements with no associated tasks
- Epics with no tasks

For each issue, suggest the workflow that resolves it (usually `spec-interview` to enrich, `spec-plan` to add tasks, or manual edit).
