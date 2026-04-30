---
context: fork
argument-hint: [EPIC-xxx | TASK-xxx]
allowed-tools:
  - Task
  - TaskOutput
  - Read
  - Edit
  - Write
  - Skill
  - AskUserQuestion
  - TodoWrite
  - mcp__morphllm__edit_file
  - mcp__sequential-thinking__sequentialthinking
  - Bash(specctl *)
  - Bash(rg *)
  - Bash(fd *)
  - Bash(wc *)
  - Bash(head *)
  - Bash(tail *)
  - Bash(date *)
  - Bash(basename *)
  - Bash(cat *)
  - Bash(mkdir *)
  - Bash(git checkout *)
  - Bash(git branch *)
  - Bash(git status *)
  - Bash(git diff *)
  - Bash(git log *)
  - Bash(git rev-parse *)
  - Bash(git push *)
  - Bash(git show *)
  - Bash(make *)
  - Bash(gh pr *)
description: Main workflow - select, plan, implement, verify, done
---

# Spec Work

Full development workflow. One task per session, with user control at every step.

## Usage

```
/spec:work                      # next ready task (respects dependencies)
/spec:work EPIC-xxx             # next ready task in specific epic
/spec:work TASK-xxx             # specific task
```

---

## Step 0: Check State

```bash
specctl status 2>/dev/null || echo "NO_SPEC"
```

**If NO_SPEC**: "Run `/spec:init` first." Stop.

**Check for interrupted session:**

```bash
specctl session show 2>/dev/null
branch=$(git branch --show-current 2>/dev/null)
```

**If session exists**: Show recovery info and offer to resume:

```bash
specctl session resume
```

Present: "Found interrupted session: {task} at step {step}. Resume or clear?"

| Header  | Question                  | Options                                                                       |
| ------- | ------------------------- | ----------------------------------------------------------------------------- |
| Session | Found interrupted session | 1. **Resume** - Continue from {step}<br>2. **Clear & pick new** - Start fresh |

**If resuming**: Jump to the appropriate step based on session step value.

---

## Step 1: Select Task

**If TASK-xxx argument**: Use that task.

**If EPIC-xxx argument**: Get ready tasks from that epic.

**Otherwise**: Get next ready task (any epic).

```bash
# Get ready tasks (respects dependencies, priority-ordered)
specctl ready                           # all ready tasks
specctl ready --epic EPIC-xxx           # ready tasks in specific epic
```

**If no ready tasks**:

- Check blocked tasks: `specctl ready` shows blockers
- "No tasks ready. Check blocked tasks or create new work."
- Stop.

**Load task:**

```bash
specctl show TASK-xxx
```

Read task file. Check for epic link and requirement link.

**Load context:**

- Epic file (if `epic:` field exists)
- Requirement file (if `implements:` in epic)
- Relevant `CONTEXT.md`, `CONTEXT-MAP.md`, and ADRs if present
- `.out-of-scope/` records if the task touches a previously rejected concept

**Mark in-progress:**

```bash
specctl start TASK-xxx
```

**Present:**

```
## Session

**Progress**: {done}/{total} tasks
**Task**: TASK-xxx
**Epic**: EPIC-xxx (if any)
**Priority**: {priority}
**Blocked by**: {deps or "none - ready to start"}

---

{task content}

---

### Context
**Epic**: {epic overview}
**Requirement**: {requirement summary}
```

**STOP**: `AskUserQuestion` - "Work on this task?"

| Header  | Question                 | Options                                                                                                                              |
| ------- | ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------ |
| Confirm | Start work on {task_id}? | 1. **Yes, proceed** - Start planning<br>2. **Different task** - Pick another<br>3. **View full context** - Show epic and requirement |

---

## Step 2: Plan

**Update session step:**

```bash
specctl session step planning
```

**Check for missing human context:**

If the task needs a product/design decision, credentials, external access, or manual validation before safe implementation, ask the user before spawning agents.

**Spawn spec-planner:**

```
Task(
  subagent_type="spec-planner",
  prompt="Create implementation plan.
  Task: {task content}
  Epic: {epic content}
  Requirement: {requirement content}
  Learn codebase style, domain vocabulary, and relevant ADRs.
  Surface missing human decisions or access as blockers.
  Return actionable plan with tests for success and error/edge cases."
)
```

**Persist plan:** Append plan summary to task file under `## Plan` section.

**Present plan.**

**STOP**: `AskUserQuestion` - "Approve this plan?"

| Header | Question                          | Options                                                                                                                            |
| ------ | --------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| Plan   | Approve this implementation plan? | 1. **Yes, implement** - Start coding<br>2. **Modify plan** - I'll explain changes<br>3. **More research** - Explore codebase first |

---

## Step 3: Implement

**Update session step:**

```bash
specctl session step implementing
```

**Create branch:**

```bash
git checkout -b "task/$task_id" 2>/dev/null || git checkout "task/$task_id"
```

Note: BASE_COMMIT is already tracked in SESSION.yaml from `specctl start`.

**Check memory for pitfalls/conventions:**

```bash
# If memory exists, read it before implementing
if [ -d .spec/memory ]; then
  cat .spec/memory/pitfalls.md 2>/dev/null
  cat .spec/memory/conventions.md 2>/dev/null
fi
```

Mention any relevant pitfalls/conventions to the engineer agent.

**TodoWrite** from plan steps.

**Ask about implementation approach:**

| Header | Question                           | Options                                                                                                                                                                                                                  |
| ------ | ---------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Mode   | How should we implement this task? | 1. **Solo engineer** - Single agent implements<br>2. **Implementation pair** - Engineer + test specialist work as team (tests written in parallel)<br>3. **Team research first** - Explore with team before implementing |

**If Solo engineer** (default):

Detect language from task files or epic, then spawn appropriate agent:

```
Task(
  subagent_type="{go|python|typescript}-engineer",
  prompt="Implement: {task description}
  Plan: {plan}
  Return proposals only - do not apply edits."
)
```

**Apply proposals** with user approval (each edit shown).

**If Implementation pair**:

Create an agent team with engineer + test specialist:

```
Create an agent team to implement this task.

Spawn two teammates:
- Primary: {go|python|typescript}-engineer
  Writes implementation code following the plan

- Secondary: {go|python|typescript}-tests
  Writes tests in parallel, identifies coverage gaps

Have them coordinate:
1. Engineer proposes implementation
2. Test specialist proposes tests simultaneously
3. Both review each other's work
4. Converge on final implementation + tests

Return proposals only - do not apply edits.
```

**Apply proposals** from both teammates with user approval.

**If Team research first**:

Create an agent team to research before implementing:

```
Create a research team to explore this feature.

Spawn teammates:
- Explore: Find similar implementations in codebase
- {go|python|typescript}-engineer: Propose architecture
- {go|python|typescript}-tests: Identify testability concerns

Have them share findings and converge on approach.
```

After research, proceed with solo engineer or implementation pair based on findings.

---

## Step 4: Verify (Max 3 Attempts)

**Update session step:**

```bash
specctl session step testing
```

```bash
make build && make test && make lint
```

**If pass**: Continue to Step 5.

**If fail (attempt < 3)**:

- Show errors
- Fix issues
- Re-verify

**If fail (attempt = 3)**:

**STOP**: `AskUserQuestion` - "Verify failed 3 times"

| Header  | Question                               | Options                                                                                                                  |
| ------- | -------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| Blocked | Verification failed 3 times. What now? | 1. **Help me fix** - Continue debugging<br>2. **Skip verify** - Mark done anyway<br>3. **Stop** - Leave task in progress |

---

## Step 5: Complete

**Update session step:**

```bash
specctl session step completing
```

**Collect evidence:**

```bash
# Files changed
git diff --name-only HEAD~1 2>/dev/null || git diff --name-only --cached

# Commits
git log --oneline -3
```

**Mark done with evidence:**

```bash
specctl done TASK-xxx \
  --summary "Brief summary of what was done" \
  --files "file1.ts,file2.ts" \
  --commits "abc123" \
  --tests "make test passed; acceptance criteria verified"
```

---

## Step 6: Capture Learnings (Optional)

**Ask user about learnings:**

| Header | Question                              | Options                                                                                                                        |
| ------ | ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| Memory | Record any lesson or follow-up task? | 1. **Record note** - Pitfall, convention, domain term, or out-of-scope decision<br>2. **File task** - New task found<br>3. **No** - Continue |

**If recording note:** ask for the note and save it where it belongs:

- Pitfall or convention → `.spec/memory/`
- Domain term → `CONTEXT.md` if the user approves the wording
- Rejected enhancement/approach → `.out-of-scope/<concept>.md`

**If filing discovered task:**

Ask user to describe the task, then create it:

```
Skill(skill="spec:new", args="task {slug}")
```

After creation, link it back:

```bash
specctl dep add TASK-{new-slug} $task_id --type discovered-from
```

Print: "Filed TASK-{slug} as discovered-from {task_id}."

---

## Step 7: Review & Commit (User Choice)

**Update session step:**

```bash
specctl session step reviewing
```

**Show scoped diff (only this task's changes):**

```bash
# Get BASE_COMMIT from session
BASE_COMMIT=$(grep "base_commit:" .spec/SESSION.yaml 2>/dev/null | cut -d' ' -f2)
git diff $BASE_COMMIT..HEAD --stat
```

**STOP**: `AskUserQuestion` - "Task complete. What next?"

| Header | Question                                                 | Options                                                                                                                                                                                       |
| ------ | -------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Next   | Task implementation complete. What would you like to do? | 1. **Review changes** - Review only this task's diff<br>2. **Commit now** - Create commit<br>3. **Push & PR** - Commit, push, create PR<br>4. **Continue to next task** - Skip commit for now |

### If Review

Pass scoped diff to review agent:

```bash
# Get only this task's changes
BASE_COMMIT=$(grep "base_commit:" .spec/SESSION.yaml 2>/dev/null | cut -d' ' -f2)
git diff $BASE_COMMIT..HEAD > /tmp/task-diff.patch
```

```
Skill(skill="reviewing-code")
# Review focuses on /tmp/task-diff.patch content
```

### If Commit

```
Skill(skill="committing-code")
```

### If Push & PR

```bash
git push -u origin "task/$task_id"
gh pr create --title "feat: {task title}" --body "Implements TASK-xxx from EPIC-xxx"
```

---

## Step 8: Next Task

Note: Session is automatically cleared when task is marked done with `specctl done`.

**Check for more ready tasks:**

```bash
specctl ready --epic EPIC-xxx  # if working on epic
specctl ready                  # otherwise
```

**Summary:**

```
## Done

**Task**: TASK-xxx
**Summary**: {done-summary}
**Files**: {changed files}

**Progress**: {done}/{total} tasks in epic

### Next Ready Tasks
{list from specctl ready}

Continue: `/spec:work` or `/spec:work EPIC-xxx`
```

---

## Key Principles

1. **User control**: Every edit shown for approval
2. **Dependency respect**: `specctl ready` orders by dependencies
3. **Evidence tracking**: `specctl done` records what was done
4. **Suggestions not automation**: Review and commit are offered, not forced
5. **One task per session**: Complete fully before starting next
