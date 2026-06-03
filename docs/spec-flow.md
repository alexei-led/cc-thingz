# Spec flow

Spec flow is a lightweight spec-driven workflow for agent coding sessions. It is more structured than an in-chat TODO list because task state, dependencies, resume points, and completion evidence live in `.spec/` files. It is less autonomous than Ralphex-style plan/execute loops or hosted workflow features because the user stays in the loop: the agent plans one slice, asks before writing, executes one task, verifies it, then checkpoints or closes it.

Use it when you want durable project memory without handing the whole backlog to an autonomous runner.

## Flow

```text
Idea / bug / project gap
  ↓
Plan one useful slice
  ↓
Create or refine TASK-<slug>.md
  ↓
Start one task session
  ↓
Implement within the approved task
  ↓
Verify with project-appropriate checks
  ↓
Review diff
  ↓
Checkpoint or mark done with evidence
  ↓
Pick next ready task
```

## What it is

- A simple markdown-backed task loop.
- One task at a time.
- Durable stop/resume through `.spec/SESSION.yaml` and checkpoints.
- Dependency-aware readiness through `blocked-by`.
- Validation that rejects vague placeholder tasks.
- Human-approved planning and code changes.

## What it is not

- Not a full PRD system.
- Not an autonomous backlog runner.
- Not a replacement for design discussion.
- Not a heavyweight project-management database.
- Not a command that generates implementation plans for you.

Planning stays in the `spec-flow` skill or normal agent planning mode. `specctl` only manages state.

## Files

- `.spec/tasks/TASK-*.md` — executable vertical slices. Required for work.
- `.spec/epics/EPIC-*.md` — optional task groups for multi-step changes.
- `.spec/reqs/REQ-*.md` — optional WHY/WHAT context for ambiguous work.
- `.spec/SESSION.yaml` — active task, step, and base commit.
- `.spec/PROGRESS.md` — append-only activity log.

## Task quality

A task is ready to execute when it has:

- a clear `## Description`
- observable `## Acceptance`
- meaningful `## Files` or scope notes
- real blockers listed in `blocked-by`
- `status: todo`
- passing `scripts/specctl validate`

Draft tasks from `scripts/specctl new task <slug>` intentionally start with placeholders. Fill them in during planning before execution.

## Commands

Initialize or inspect:

```bash
scripts/specctl init
scripts/specctl status
scripts/specctl validate
```

Plan one task with the skill, then create/refine state:

```bash
scripts/specctl new task <slug>
scripts/specctl validate
scripts/specctl ready
```

Execute one task:

```bash
scripts/specctl start TASK-<slug>
# agent implements and verifies the approved task
scripts/specctl session handoff
```

Stop and resume:

```bash
scripts/specctl checkpoint --message "where to resume"
scripts/specctl session handoff
```

Close with evidence:

```bash
scripts/specctl done TASK-<slug> \
  --summary "what changed" \
  --tests "checks passed or not run: reason" \
  --files "changed files or none" \
  --commits "sha or none"
```

## Example

User asks: "Add CSV export."

1. The agent uses `spec-flow` to ask only the missing planning questions.
2. It proposes one task: `TASK-export-csv`.
3. After approval, it writes a task with acceptance criteria and likely files.
4. `scripts/specctl validate` rejects the task if it is still vague.
5. The agent starts the task, implements only that slice, and runs relevant checks.
6. If interrupted, it checkpoints with the current step and diff.
7. When finished, it marks done with summary, checks, files, and commit evidence.

## Rules of thumb

- If it fits in one focused session, make one task.
- If it needs ordering, use `blocked-by`.
- If it needs many tasks, add an `EPIC-*`.
- If the goal is unclear, write a small `REQ-*` first.
- If new work appears during execution, file a follow-up task instead of expanding scope.

Do not edit task status or session state by hand. Use `scripts/specctl`.
