---
description: Use when planning, executing, checkpointing, finishing, or inspecting
  lightweight spec-driven work. Runs one task at a time using `.spec/` markdown files
  and the bundled `specctl` helper. NOT for broad product discovery beyond a short
  requirement interview. NOT for generic implementation planning that does not read
  or write `.spec/` files.
name: spec-flow
---

# Spec flow

Lightweight spec loop for controlled task-by-task work.

Loop: plan one slice → execute one task → checkpoint or close → repeat.

`specctl` owns state. Do not edit task status or `.spec/SESSION.yaml` by hand.

## Read first

- `references/method.md` for artifact shapes, planning rules, task quality, and mini-interview guidance.
- `references/specctl-commands.md` for CLI commands.

## State model

- `.spec/tasks/TASK-*.md` — executable vertical slices. Required for work.
- `.spec/epics/EPIC-*.md` — optional group for multi-task plans.
- `.spec/reqs/REQ-*.md` — optional WHY/WHAT context for ambiguous work.
- `.spec/SESSION.yaml` — active task, step, base commit.
- `.spec/PROGRESS.md` — append-only activity log.

Task states: `todo`, `in-progress`, `done`.

## Common flows

New project:

```bash
scripts/specctl init
```

Then plan the first executable slice. Do not build a full backlog unless the user asks.

Existing project:

1. Inspect current code and project instructions.
2. Create the smallest task that can be verified.
3. Link optional REQ/EPIC context only when it reduces ambiguity.

Stop and resume:

```bash
scripts/specctl checkpoint --message "<where to resume>"
scripts/specctl session handoff
```

Iterate:

```bash
scripts/specctl ready
scripts/specctl start TASK-<id>
# implement + verify
scripts/specctl done TASK-<id> --summary "..." --tests "..."
```

## Modes

### Orient

Use when the user asks for status, next task, resume, health, or what to do next.

```bash
scripts/specctl status
scripts/specctl ready
scripts/specctl session handoff
scripts/specctl validate
```

Report active session, next ready task, validation issues, and the smallest next action.

### Plan

Use when the user has an idea, requirement, bug, or project gap and wants an executable plan.

1. Run `scripts/specctl init`.
2. Check status/session before changing files.
3. Ask 3-5 questions only if the slice is unclear.
4. Optionally scan the codebase for relevant files and patterns.
5. Draft the smallest useful artifact set:
   - one clear slice → one `TASK-*`
   - several slices → one `EPIC-*` plus tasks
   - unclear WHY/WHAT → one `REQ-*` first
6. Show the proposed plan and ask before writing.
7. Write with `scripts/specctl new task <slug>` when possible, then edit details.
8. Run `scripts/specctl validate` and `scripts/specctl ready`.

Do not write implementation code in plan files.

### Execute

Use when the user wants to work, continue, or implement a task.

1. Run `scripts/specctl status` and `scripts/specctl session show`.
2. If a session exists, ask whether to resume, checkpoint, clear, or stop.
3. Select with `scripts/specctl ready` or verify the named task with `scripts/specctl show TASK-<id>`.
4. Start with `scripts/specctl start TASK-<id>`.
5. Make a short implementation plan; ask before editing.
6. Implement only the approved task.
7. Run project-appropriate checks from project instructions and changed files.
8. Show scoped diff or `scripts/specctl session handoff` before close.
9. Close with `scripts/specctl done ...` or checkpoint with `scripts/specctl checkpoint`.

### Checkpoint or close

Use when the user stops, switches context, or finishes.

Checkpoint:

```bash
scripts/specctl checkpoint --message "<where to resume>"
```

Close:

```bash
scripts/specctl done TASK-<id> \
  --summary "<what changed>" \
  --tests "<checks passed or not run: reason>" \
  --files "<changed files or none>" \
  --commits "<sha or none>"
```

`specctl done` needs `--summary` and `--tests` unless the user explicitly approves `--force`.

## Guardrails

- One task is the execution unit.
- Checkpoint before stopping or switching.
- Keep work inside the approved task.
- File follow-up tasks instead of expanding scope.
- Verification is adaptive; do not assume every project has `make`.
- User approval is required before writing plan files, editing code, forcing state, or clearing another session.

## Output

```markdown
## Spec flow

Mode: orient | plan | execute | checkpoint | close
Task: <TASK-id or none>
Status: <ready | in-progress | checkpointed | done | blocked>
Evidence: <commands/tests/checks or skipped reason>
Next: <one command or action>
```

## Failure handling

- No `.spec/`: run or offer `scripts/specctl init`.
- Active session conflicts: show handoff and ask before switching.
- No ready tasks: show blockers; plan new work or finish blockers.
- Validation fails: fix the smallest artifact issue before work.
- Verification fails: fix within scope, checkpoint, or stop; do not mark done.
