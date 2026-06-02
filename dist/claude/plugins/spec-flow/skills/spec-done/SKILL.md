---
allowed-tools:
- Read
- Write
- Edit
- Glob
- Grep
- Bash(scripts/specctl *)
- Bash(rg *)
- Bash(make *)
- Bash(git *)
- Bash(gh pr *)
- Bash(date *)
- Bash(echo *)
argument-hint: '[TASK-id]'
context: fork
description: Mark a task complete with evidence. Use when finishing a task, discovering
  which in-progress tasks look done from git history, or verifying quality gates before
  closing out. Handles follow-up task creation and durable learnings. NOT for reporting
  progress (spec-status).
model: sonnet
name: spec-done
user-invocable: true
---

# `spec done` — mark a task complete

CLI at `scripts/specctl`. Three flavors:

- **Mark a specific task done** — user names a task and says it's finished.
- **Discover potentially done tasks** — user wants to know which in-progress tasks look complete based on git evidence.
- **Verify then mark** — user wants tests/lint/build to pass before changing status.

## Mark a specific task

### Step 1: Find the task

Look up the task file under `.spec/tasks/` matching the user-supplied id (add the `TASK-` prefix if missing). If not found, say "Task not found." and stop.

### Step 2: Check current status

If the task is already `done`, say "Already complete." and stop. Otherwise continue.

### Step 3: Verify completion evidence

Before marking done, collect or confirm:

- Acceptance criteria satisfied
- Test / lint / build evidence (or an explicit reason they were not run)
- Files changed
- Unresolved follow-up work
- Any domain term, ADR, or out-of-scope decision discovered

If evidence is missing, ask the user before marking done.

### Step 4: Update status

Edit the task frontmatter: `status: todo` → `status: done`.

### Step 5: Log

```bash
echo "$(date +%H:%M) DONE TASK-<id>" >> .spec/PROGRESS.md
```

Output:

```
## Done

Marked complete: TASK-<id>
```

### Step 6: Land the plane

Check for uncommitted work:

```bash
git status --porcelain
```

If non-empty, offer to commit (delegate to the runtime's commit workflow).

Record durable decisions if needed:

- New domain term → `CONTEXT.md`
- Architectural decision → `docs/adr/`
- Rejected enhancement → `.out-of-scope/<concept>.md`

If a follow-up task was discovered, create it using the `spec-new` skill and link it back: `scripts/specctl dep add TASK-<new> TASK-<id> --type discovered-from`.

## Discover potentially done tasks

First check if any tasks have `status: in-progress`. If none exist, say "No in-progress tasks found." and stop.

For each task with `status: todo` or `status: in-progress`:

```bash
git log --oneline -- <files from task body>
```

Heuristics for "looks done":

- All files listed in the task have recent commits
- Acceptance criteria keywords appear in commit messages
- Branch `task/<id>` has merged commits

Surface candidates with evidence; ask the user which to mark done. For each one chosen, fall back to the "mark specific" flow.

## Verify then mark

```bash
make build && make test && make lint
```

- Pass → run the "mark specific" flow with the test/build/lint results recorded as evidence.
- Fail → show errors, offer fixes, do NOT mark done.

Record the verification output in the evidence collected in step 3.
