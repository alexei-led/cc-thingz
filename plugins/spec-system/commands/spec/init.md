---
context: fork
argument-hint: [path/to/spec.md]
allowed-tools:
  - Task
  - TaskOutput
  - Skill
  - TodoWrite
  - Read
  - Write
  - AskUserQuestion
  - Glob
  - Bash(rg *)
  - Bash(fd *)
  - Bash(git *)
  - Bash(mkdir *)
  - Bash(date *)
  - Bash(echo *)
description: Initialize or extend spec-driven project
---

# Spec Init

Initialize new project or add requirements to existing one.

## Usage

```
/spec:init                      # new project with brainstorming
/spec:init docs/spec.md         # generate reqs from existing docs
```

---

## Step 1: Check Existing

```bash
ls .spec/ 2>/dev/null && echo "SPEC_EXISTS"
```

---

## Mode: New Project (no .spec/)

### Step 2: Brainstorm

Use the brainstorming skill:

```
Skill(skill="brainstorming-ideas", args="What are we building? Let's explore requirements.")
```

Discover:

- What problem are we solving?
- Who are the users?
- Core capabilities needed?
- Tech stack?

Group findings into requirement topics (auth, data, ui, api, etc.).

### Step 3: Confirm

`AskUserQuestion` - "Does this capture the project? [Yes / Adjust / Start over]"

### Step 4: Create Structure

```bash
mkdir -p .spec/reqs .spec/tasks
echo "# Progress" > .spec/PROGRESS.md
echo "$(date +%H:%M) INIT project" >> .spec/PROGRESS.md
```

**Create REQ-\*.md files** for each requirement topic:

```yaml
---
id: REQ-{topic}
version: 1
priority: normal
---
# {Title}

{Description}

{Success criteria}
```

**Create initial TASK-\*.md files**:

```yaml
---
id: TASK-{name}
status: todo
priority: normal
implements: REQ-{topic}
---
# {Title}

{Vertical slice description, acceptance criteria, and out-of-scope boundaries}
```

### Step 5: Summary

```
## Ready

.spec/
├── PROGRESS.md
├── reqs/       ({N} requirements)
└── tasks/      ({M} tasks)

Next: `/spec:work`
```

---

## Mode: Add Requirements (.spec/ exists + file argument)

If SPEC_EXISTS and file path provided:

### Step 2: Read Input

Read provided document(s). Extract:

- Core concept
- Features (explicit and implied)
- Constraints
- Data entities

### Step 3: Generate Requirements

Organize by topic. For each:

```yaml
---
id: REQ-{topic}-{name}
version: 1
priority: normal
---
# {Title}

{Description from source}

{Success criteria}
```

### Step 4: Confirm

`AskUserQuestion` - "Generated {N} requirements. Proceed? [Write / Preview / Adjust]"

### Step 5: Write

```bash
mkdir -p .spec/reqs
echo "$(date +%H:%M) GEN {N} requirements" >> .spec/PROGRESS.md
```

Write each REQ-\*.md file.

```
## Added

{N} requirements created from {source}.
Next: `/spec:new task {name}` or `/spec:work`
```

---

## Mode: Already Initialized (no file argument)

If SPEC_EXISTS and no file:

```
## Already Initialized

.spec/ exists with {N} tasks, {M} requirements.

Use:
- `/spec:work` - continue development
- `/spec:status` - see progress
- `/spec:init docs/spec.md` - add requirements from docs
```

---
