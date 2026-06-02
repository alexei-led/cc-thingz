---
description: Implement the next ready task. Use when starting a development session
  — selects the highest-priority ready task, plans with a specialist subagent, implements
  with approval at every step, verifies quality gates, and commits. One task per session.
  NOT for batch task execution or planning new work — use spec-plan for planning.
name: spec-work
---

# `spec work` — main implementation workflow

CLI at `scripts/specctl`. Full development workflow for one task per session, with user control at every step.

Input: empty (next ready task), `EPIC-id` (next ready in that epic), or `TASK-id` (specific task).

## Step 0: Check state

```bash
scripts/specctl status 2>/dev/null || echo "NO_SPEC"
```

If `NO_SPEC`: "Use the `spec-init` skill to initialize the project first." Stop.

### Check for interrupted session

```bash
scripts/specctl session show 2>/dev/null
git branch --show-current 2>/dev/null
```

If a session is in progress, ask the user a multi-choice question: "Found interrupted session: <task> at step <step>. Resume or clear?"

- Resume — continue from `<step>`
- Clear & pick new — start fresh

If resuming, jump to the step recorded in `SESSION.yaml`.

## Step 1: Select task

- `TASK-id` argument → use it.
- `EPIC-id` argument → `scripts/specctl ready --epic EPIC-id` and pick the highest-priority ready task.
- Otherwise → `scripts/specctl ready` and pick the highest-priority ready task.

If no ready tasks:

```bash
scripts/specctl ready   # shows blockers
```

Tell the user: "No tasks ready. Check blocked tasks or create new work." Stop.

### Load task and context

```bash
scripts/specctl show TASK-<id>
```

Read the task file. Check for epic link (`epic:` field) and requirement link (`implements:` in the epic).

Read when present:

- Epic file
- Requirement file
- `CONTEXT.md`, `CONTEXT-MAP.md`, ADRs
- `.out-of-scope/` records if the task touches a rejected concept

### Mark in-progress

```bash
scripts/specctl start TASK-<id>
```

### Present

```
## Session

Progress: <done>/<total> tasks
Task: TASK-<id>
Epic: EPIC-<id> (if any)
Priority: <priority>
Blocked by: <deps or "none — ready to start">

---

<task content>

---

### Context
Epic: <epic overview>
Requirement: <requirement summary>
```

Ask multi-choice: "Work on this task?"

- Yes, proceed — start planning
- Different task — pick another
- View full context — show epic and requirement

## Step 2: Plan

Update session step: `scripts/specctl session step planning`.

### Missing human context

If the task needs a product/design decision, credentials, external access, or manual validation before safe implementation, ask the user before spawning any agents.

### Delegate planning

If the runtime supports subagents, delegate to a planning specialist (the `reviewer` role running this skill). Prompt:

```
Create an implementation plan.
Task: <task content>
Epic: <epic content>
Requirement: <requirement content>
Learn codebase style, domain vocabulary, and relevant ADRs.
Surface missing human decisions or access as blockers.
Return actionable plan with tests for success and error/edge cases.
```

If subagents are unavailable, produce the plan inline.

### Persist plan

Append the plan summary to the task file under `## Plan`.

### Approve plan

Ask multi-choice: "Approve this implementation plan?"

- Yes, implement — start coding
- Modify plan — user explains
- More research — explore codebase first

## Step 3: Implement

Update session step: `scripts/specctl session step implementing`.

### Branch

```bash
git checkout -b "task/<id>" 2>/dev/null || git checkout "task/<id>"
```

`BASE_COMMIT` is already recorded in `.spec/SESSION.yaml` from `scripts/specctl start`.

### Memory check

If `.spec/memory/` exists, read `pitfalls.md` and `conventions.md` before implementing and surface relevant items to the engineer agent.

### Track sub-steps

Use the runtime's task-tracking facility (if any) to materialize the plan as tracked sub-steps.

### Implementation mode

Ask the user which mode to use — solo engineer (default), implementation pair, or team research first — then delegate accordingly. For the mode options, agent composition, and delegation prompts, read `references/implementation-modes.md`.

## Step 4: Verify (max 3 attempts)

Update session step: `scripts/specctl session step testing`.

```bash
make build && make test && make lint
```

- Pass → Step 5.
- Fail (attempt < 3) → show errors, fix, re-verify.
- Fail (attempt 3) → ask multi-choice: "Verification failed 3 times. What now?"
  - Help me fix — continue debugging
  - Skip verify — mark done anyway
  - Stop — leave task in progress

## Step 5: Complete

Update session step: `scripts/specctl session step completing`.

Collect evidence:

```bash
git diff --name-only HEAD~1 2>/dev/null || git diff --name-only --cached
git log --oneline -3
```

Mark done with evidence:

```bash
scripts/specctl done TASK-<id> \
  --summary "<brief>" \
  --files "file1.ts,file2.ts" \
  --commits "<sha>" \
  --tests "make test passed; acceptance criteria verified"
```

## Step 6: Capture learnings (optional)

Ask multi-choice: "Record any lesson or follow-up task?"

- Record note — pitfall, convention, domain term, or out-of-scope decision
- File task — new task found
- No — continue

For where each note type lands and how to link a discovered task back to this one, read `references/capture-learnings.md`.

## Step 7: Review & commit (user choice)

Update session step: `scripts/specctl session step reviewing`.

Show scoped diff (only this task's changes):

```bash
BASE_COMMIT=$(grep "base_commit:" .spec/SESSION.yaml 2>/dev/null | cut -d' ' -f2)
git diff $BASE_COMMIT..HEAD --stat
```

Ask multi-choice: "Task implementation complete. What would you like to do?"

- Review changes — review only this task's diff
- Commit now — create commit
- Push & PR — commit, push, create PR
- Continue to next task — skip commit for now

### Review

Delegate code review to a review workflow. Pass the scoped diff (`$BASE_COMMIT..HEAD`) as the review scope.

### Commit

Delegate to a commit workflow that handles staging, grouping, and writing commit messages.

### Push & PR

```bash
git push -u origin "task/<id>"
gh pr create --title "feat: <task title>" --body "Implements TASK-<id> from EPIC-<id>"
```

## Step 8: Next task

`scripts/specctl done` clears the session automatically.

```bash
scripts/specctl ready --epic EPIC-<id>   # if working on an epic
scripts/specctl ready                    # otherwise
```

Summary:

```
## Done

Task: TASK-<id>
Summary: <done-summary>
Files: <changed files>

Progress: <done>/<total> tasks in epic

### Next ready tasks
<list from specctl ready>

Continue: `spec-work` | `spec-work EPIC-<id>`
```

## Key principles

- User control at every decision gate — task selection (Step 1), plan approval (Step 2), implementation mode (Step 3), and post-apply review of the scoped diff before commit (Step 7). The `engineer` applies edits autonomously within the approved plan; review is post-apply, not per-edit.
- Dependency-aware selection (`scripts/specctl ready` orders by deps and priority).
- Evidence-tracked completion (`scripts/specctl done` records what was done).
- Review and commit are offered, not forced.
- One task per session — complete fully before starting the next.
