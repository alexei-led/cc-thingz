---
{"description":"Use when planning, executing, checkpointing, finishing, or inspecting lightweight spec-driven work. Runs one task at a time using `.spec/` markdown files and the bundled `specctl` helper. NOT for broad product discovery beyond a short requirement interview. NOT for generic implementation planning that does not read or write `.spec/` files.","name":"spec-flow"}
---
<!-- Pi platform guidance -->
<!-- Use installed Pi tool names exactly, including extension toolsets such as Task*, Monitor*, and Loop*. -->
<!-- When available, track work with Task* (`todo` is the fallback), run long or background commands with MonitorCreate, and schedule follow-up with LoopCreate instead of sleep/poll loops. -->


# Spec flow

Lightweight loop for controlled work, one task at a time: plan one slice, execute
one task, checkpoint or close, repeat.

`scripts/specctl` (written `specctl` below) owns state. Do not edit task status
or `.spec/SESSION.yaml` by hand. `references/specctl-commands.md` lists every command.
`references/method.md` covers task quality, templates, the planning output, and
the mini-interview.

## State model

- `.spec/tasks/TASK-*.md` — executable vertical slices. Required for work.
- `.spec/epics/EPIC-*.md` — optional group for multi-task plans.
- `.spec/reqs/REQ-*.md` — optional WHY/WHAT context for ambiguous work.
- `.spec/SESSION.yaml` — active task, step, base commit.
- `.spec/PROGRESS.md` — append-only activity log.

Task states: `todo`, `in-progress`, `done`.

## Modes

### Orient

For status, the next task, resume, or health: run `specctl status`, `ready`,
`session handoff`, and `validate`. Report the active session, the next ready task,
validation issues, and the smallest next action.

### Plan

For an idea, requirement, bug, or project gap that needs an executable plan.
Done when the smallest useful artifact set exists and passes `specctl validate`,
and its first task appears in `specctl ready` (a REQ-only plan has no ready task
yet). Create tasks and requirements with `specctl new task|req`, then fill in
the details; write an `EPIC-*` file by hand. Pick the smallest set:

- one clear slice: one `TASK-*`
- several slices: one `EPIC-*` plus tasks
- unclear WHY or WHAT: one `REQ-*` first

Run `specctl init` when `.spec/` is missing, and check status and session before
changing files. In an existing project, read the code and project instructions
first, and link REQ or EPIC context only when it reduces ambiguity. Ask
questions only when the slice is unclear. Show the proposed plan before writing it
unless the user already authorized that scope. Build a full backlog only on
request, and keep implementation code out of plan files.

### Execute

For work, continue, or implement. Done when the relevant build/test/lint checks
pass on what you changed, or you name each check that did not run and why. Before
closing, confirm the acceptance criteria and show the scoped diff or
`specctl session handoff`; if the task cannot finish, checkpoint it instead.

- Check `specctl status` and `specctl session show` first. Resume a matching
  session when the user asks to continue; ask before replacing a conflicting one.
- Pick the task from `specctl ready` or verify the named one with `specctl show`,
  then `specctl start TASK-<id>`.
- Share a short implementation plan unless that scope is already approved.
  Implement only this task; file follow-up tasks instead of widening scope.
- Take checks from the project instructions and the changed files; not every
  project has `make`.

### Checkpoint or close

Checkpoint before stopping or switching context:

```bash
scripts/specctl checkpoint --message "<where to resume>"
```

Close a finished task:

```bash
scripts/specctl done TASK-<id> \
  --summary "<what changed>" \
  --tests "<checks passed, or not run: reason>" \
  --files "<changed files or none>" \
  --commits "<sha or none>"
```

`--summary` and `--tests` are required unless the user approves `--force`. They
record your evidence; `specctl` does not run or certify checks. Name the commands
and results, including skip reasons such as `--tests "not run: docs-only task"`.

## Authorization

Approval covers the agreed plan and implementation scope; do not ask again at each
mechanical step. Ask when scope changes, before using `--force`, or before
clearing a conflicting session.

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

- No `.spec/`: run or offer `specctl init`.
- No ready tasks: show blockers; plan new work or finish the blockers.
- Validation fails: fix the smallest artifact issue before work.
- Verification fails: fix within scope, checkpoint, or stop; do not mark done.
