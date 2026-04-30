---
model: haiku
argument-hint: [TASK-xxx | discover | verify TASK-xxx]
allowed-tools:
  - Read
  - Edit
  - Skill
  - AskUserQuestion
  - Bash(fd *)
  - Bash(rg *)
  - Bash(date *)
  - Bash(echo *)
  - Bash(basename *)
  - Bash(make *)
  - Bash(git *)
  - Bash(specctl *)
description: Mark task complete with verification, evidence, handoff, and optional discovery
---

# Spec Done

Mark task(s) complete. Can discover potentially done tasks.

## Usage

```
/spec:done TASK-xxx             # mark specific task done
/spec:done auth-login           # auto-prefix TASK-
/spec:done discover             # find tasks that might be done
/spec:done verify TASK-xxx      # run tests before marking
```

## Arguments

$ARGUMENTS

Parse: TASK-ID, or mode (discover, verify).

---

## Mode: Mark Specific Task (default)

If argument is a task ID (not "discover" or "verify"):

### Step 1: Find task

```bash
# Add TASK- prefix if needed
fd "TASK-{id}.md" .spec/tasks/
```

**If not found**: "Task not found." Stop.

### Step 2: Check current status

```bash
rg '^status:' TASK_FILE
```

**If already done**: "Already complete." Stop.

### Step 3: Verify completion evidence

Before marking done, collect or confirm:

- acceptance criteria satisfied
- tests/lint/build evidence, or explicit reason they were not run
- files changed
- unresolved follow-up work
- any domain term, ADR, or out-of-scope decision discovered

If evidence is missing, ask before marking done.

### Step 4: Update status

```
Edit: status: todo → status: done
```

### Step 5: Log

```bash
echo "$(date +%H:%M) DONE TASK-{id}" >> .spec/PROGRESS.md
```

**Output:**

```
## Done!

Marked complete: TASK-{id}
```

### Step 6: Land the Plane

**Check for uncommitted work:**

```bash
git status --porcelain
```

If output is non-empty: offer to commit via `Skill(skill="committing-code")`.

**Record durable decisions if needed:**

- New domain term → update `CONTEXT.md` or relevant context file.
- Hard-to-reverse, surprising trade-off → offer an ADR under `docs/adr/`.
- Rejected enhancement/approach → update `.out-of-scope/<concept>.md`.

**Generate handoff:**

```bash
specctl session handoff
```

Print the output — this is context for the next session.

**Offer push:**

| Header | Question                   | Options                                                                                           |
| ------ | -------------------------- | ------------------------------------------------------------------------------------------------- |
| Push   | Push branch and create PR? | 1. **Yes, push now** - `git push -u origin $(git branch --show-current)`<br>2. **Not yet** - Skip |

Plain push is allowed. Force push is not part of this workflow.

---

## Mode: Verify Before Mark (verify TASK-xxx)

If first arg is "verify", second is task ID.

Run quality gates first:

```bash
make build && make test && make lint
```

**If fail**: "Tests failing. Fix before marking done." Stop.

**If pass**: Continue with mark (same as above).

---

## Mode: Discover (discover)

Find todo tasks that might be complete based on code evidence.

### Step 1: Find candidates

```bash
for f in $(rg -l '^status: todo' .spec/tasks/ 2>/dev/null | head -10); do
  task_id=$(basename "$f" .md | sed 's/TASK-//')
  task_name=$(echo "$task_id" | tr '-' ' ')

  # Evidence 1: Task ID in code
  code_match=$(rg -l "$task_id" --type-not md 2>/dev/null | head -1)

  # Evidence 2: Keywords from task name in code
  keyword_match=$(rg -li "$task_name" --type-not md 2>/dev/null | head -1)

  # Evidence 3: Related test file exists
  test_match=$(fd -e go -e ts -e py . | rg -i "test.*$task_id|$task_id.*test" | head -1)

  # Score: 1 point per evidence type
  score=0
  [ -n "$code_match" ] && score=$((score + 1))
  [ -n "$keyword_match" ] && score=$((score + 1))
  [ -n "$test_match" ] && score=$((score + 1))

  [ "$score" -gt 0 ] && echo "CANDIDATE ($score/3): $(basename $f .md) → ${code_match:-$keyword_match:-$test_match}"
done
```

### Step 2: Present candidates

```
## Possibly Done

| Task | Evidence Score | Found In |
|------|----------------|----------|
| TASK-auth-login | 2/3 | src/auth/login.go |
| TASK-data-schema | 1/3 | tests/schema_test.go |
```

### Step 3: Confirm

**STOP**: `AskUserQuestion` - "Mark these done? [All / Select / Skip]"

### Step 4: If confirmed

For each selected task:

```bash
# Optionally verify first
make test 2>/dev/null

# Mark done
Edit: status: todo → status: done
echo "$(date +%H:%M) DONE {task_id} (discovered)" >> .spec/PROGRESS.md
```

**Output:**

```
## Marked Done

- TASK-auth-login
- TASK-data-schema

{N} tasks marked complete.
```

---
