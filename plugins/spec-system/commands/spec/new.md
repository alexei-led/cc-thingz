---
model: haiku
argument-hint: task|req name
allowed-tools:
  - Read
  - Write
  - Glob
  - Bash(mkdir *)
  - Bash(date *)
  - Bash(echo *)
description: Create new spec document (task or req)
---

# Create Spec Document

Create a new task or requirement from template.

## Usage

```
/spec:new task auth-login              # .spec/tasks/TASK-auth-login.md
/spec:new task auth/login              # .spec/tasks/auth/TASK-login.md
/spec:new req auth-core                # .spec/reqs/REQ-auth-core.md
```

## Arguments

$ARGUMENTS

Parse: `TYPE NAME` where TYPE is task|req.

If NAME contains `/`, split into topic/name.

## Step 1: Check .spec/ exists

```bash
ls .spec/ 2>/dev/null || mkdir -p .spec/tasks .spec/reqs
```

## Step 2: Determine path

| Type | Folder               | Prefix | Example            |
| ---- | -------------------- | ------ | ------------------ |
| task | .spec/tasks/{topic}/ | TASK-  | TASK-auth-login.md |
| req  | .spec/reqs/{topic}/  | REQ-   | REQ-auth-core.md   |

## Step 3: Generate content

**Task:**

```yaml
---
id: TASK-{name}
status: todo
priority: normal
implements:
---
# {Title}

(describe the vertical slice, acceptance criteria, and out-of-scope boundaries)
```

**Req:**

```yaml
---
id: REQ-{name}
version: 1
priority: normal
---
# {Title}

(describe requirements and success criteria)
```

## Step 4: Write + Log

Write the file.

```bash
echo "$(date +%H:%M) NEW {TYPE}-{name}" >> .spec/PROGRESS.md
```

```
Created: .spec/{type}s/{TYPE}-{name}.md
```

---
