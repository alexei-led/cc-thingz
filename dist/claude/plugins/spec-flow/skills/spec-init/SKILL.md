---
allowed-tools:
- AskUserQuestion
- Read
- Write
- Glob
- Grep
- Bash(scripts/specctl *)
- Bash(mkdir *)
- Bash(date *)
- Bash(ls *)
- Bash(echo *)
argument-hint: '[doc-path]'
context: fork
description: Initialize a `.spec/` project or extract requirements from a document.
  Use when there is no `.spec/` directory yet, or to add requirements from an existing
  design doc. NOT for one-off task/req creation (spec-new) or deep PRD-quality requirement
  capture (spec-interview).
model: sonnet
name: spec-init
user-invocable: true
---

# `spec init` — initialize or extend a project

CLI at `scripts/specctl`. Three modes, picked by checking whether `.spec/` exists and whether the user passed a file path.

## Step 1: Check existing

```bash
ls .spec/ 2>/dev/null && echo "SPEC_EXISTS"
```

## Mode A: New project (no `.spec/`)

### Step 2: Brainstorm

If a brainstorming workflow is available in the runtime, use it to surface requirements. Otherwise ask the user directly:

- What problem are we solving?
- Who are the users?
- Core capabilities needed?
- Tech stack?

Group findings into requirement topics (auth, data, ui, api, etc.).

### Step 3: Confirm

Ask the user a multi-choice question: "Does this capture the project?" with options Yes / Adjust / Start over.

### Step 4: Create structure

```bash
mkdir -p .spec/reqs .spec/tasks
echo "# Progress" > .spec/PROGRESS.md
echo "$(date +%H:%M) INIT project" >> .spec/PROGRESS.md
```

Create one `REQ-<topic>.md` per requirement topic:

```markdown
---
id: REQ-<topic>
version: 1
priority: normal
---

# <Title>

<Description>

<Success criteria>
```

Create initial `TASK-<name>.md` files:

```markdown
---
id: TASK-<name>
status: todo
priority: normal
implements: REQ-<topic>
---

# <Title>

<Vertical slice description, acceptance criteria, out-of-scope boundaries>
```

### Step 5: Summary

```
## Ready

.spec/
├── PROGRESS.md
├── reqs/       (<N> requirements)
└── tasks/      (<M> tasks)

Next: use the `spec-work` skill to start implementing tasks
```

## Mode B: Add requirements (`.spec/` exists + file argument)

### Step 2: Read input

Confirm the file exists and is readable text. If not, say "File not found or not readable." and stop.

Read the user-provided document. Extract:

- Core concept
- Features (explicit and implied)
- Constraints
- Data entities

### Step 3: Generate requirements

Organize by topic. For each, create:

```markdown
---
id: REQ-<topic>-<name>
version: 1
priority: normal
---

# <Title>

<Description from source>

<Success criteria>
```

### Step 4: Confirm + write

Ask multi-choice: "Generated <N> requirements. Proceed?" with options Write / Preview / Adjust.

```bash
mkdir -p .spec/reqs
echo "$(date +%H:%M) GEN <N> requirements" >> .spec/PROGRESS.md
```

Write each `REQ-*.md` file. Suggest next: use the `spec-new` skill to create a task or the `spec-work` skill to start implementing.

## Mode C: Already initialized (no file argument)

```
## Already Initialized

.spec/ exists with <N> tasks, <M> requirements.

Use:
- `spec-work` — continue development
- `spec-status` — see progress
- `spec-init <doc.md>` — add requirements from docs
```
