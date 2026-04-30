---
model: sonnet
context: fork
description: Create epic with vertical-slice tasks from a requirement
argument-hint: REQ-xxx | <idea>
allowed-tools:
  - Task
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash(specctl *)
  - Bash(mkdir *)
  - Bash(ls *)
  - Bash(date *)
  - AskUserQuestion
---

# Spec Plan

Turn a requirement into an epic with independently grabbable vertical-slice tasks and dependencies.

**Role**: Technical planner
**Goal**: Create EPIC-_.md + TASK-_.md files with dependencies, blockers, and acceptance criteria

## Input

$ARGUMENTS

**Input types:**

- **REQ ID**: `REQ-auth` → Read requirement, create epic + tasks
- **EPIC ID**: `EPIC-auth` → Refine existing epic
- **Idea text**: `"add OAuth"` → Create REQ first via quick interview, then plan

If empty, ask: "What should I plan? Give me a REQ ID or describe the feature."

---

## Step 0: Setup

```bash
specctl init 2>/dev/null || true
mkdir -p .spec/epics .spec/tasks
```

---

## Step 1: Load Context

### If REQ ID

```bash
specctl show REQ-xxx
```

Read the requirement file for context.

### If EPIC ID

```bash
specctl show EPIC-xxx
```

Read existing epic. This is a refinement - may add/update tasks.

### If idea text

Ask 3-5 quick questions to understand scope, then proceed.
(For deep requirements, suggest `/spec:interview` instead.)

---

## Step 2: Research (Optional)

Ask user:

| Header   | Question                             | Options                                                                                                  |
| -------- | ------------------------------------ | -------------------------------------------------------------------------------------------------------- |
| Research | Should I explore the codebase first? | 1. **Yes, quick scan** - Find patterns and conventions<br>2. **No, I know the codebase** - Skip research |

### If yes, spawn research agent:

```
Task(
  subagent_type="Explore",
  prompt="Find existing patterns, conventions, and code relevant to: {requirement summary}. Look for similar implementations, reusable code, and architectural patterns.",
  run_in_background=false
)
```

Capture:

- File paths + line refs
- Existing patterns to follow
- Code to reuse
- Architectural conventions

---

## Step 3: Create Plan

### Vertical Slice Rules

Tasks should be tracer bullets, not horizontal layers.

- Each task delivers a narrow but complete path through the system.
- A completed task is demoable or independently verifiable.
- Prefer many thin slices over one thick slice.
- Avoid "schema task", then "API task", then "UI task" unless one layer is the whole product.
- Include tests in the same slice as the behavior.

If a slice needs a human decision, external access, or manual validation before it can be completed safely, capture that as a blocker or open question. Do not add a task taxonomy for it.

### Task Sizing Guide

| Size  | Files | Criteria | Action               |
| ----- | ----- | -------- | -------------------- |
| **S** | 1-2   | 1-3      | Combine with related |
| **M** | 3-5   | 3-5      | **Target size**      |
| **L** | 5+    | 5+       | Split into M tasks   |

**M is ideal** - meaningful progress, fits one session.

### Dependency Rules

- Tasks that must complete before others → `blocked-by`
- Minimize file overlap for parallel work
- Sequential S tasks → combine into M

### Plan Structure

Create mental model:

1. What vertical slices are needed?
2. What order (dependencies)?
3. What size is each task?
4. Which can run in parallel?
5. Which unresolved questions block implementation?

---

## Step 4: Present Plan for Approval

Before writing files, show the plan:

```
## Proposed Plan for {requirement}

### Epic: EPIC-{slug}
{overview}

### Tasks (in order):

1. **TASK-{slug}-1**: {title}
   - Size: M
   - Files: {expected files}
   - Blocked by: none
   - Open questions: none | {specific blocker}
   - Verifiable: {demo/check/test}

2. **TASK-{slug}-2**: {title}
   - Size: M
   - Files: {expected files}
   - Blocked by: TASK-{slug}-1
   - Open questions: none | {specific blocker}
   - Verifiable: {demo/check/test}

3. **TASK-{slug}-3**: {title}
   - Size: S
   - Files: {expected files}
   - Blocked by: none (can run parallel with task 2)
   - Open questions: none | {specific blocker}
   - Verifiable: {demo/check/test}

Does this plan look right?
```

Use AskUserQuestion:

| Header  | Question                   | Options                                                                                                                                                                       |
| ------- | -------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Approve | Does this plan look right? | 1. **Yes, create files** - Write epic and tasks<br>2. **Needs changes** - I'll explain<br>3. **Too detailed** - Simplify tasks<br>4. **Not detailed enough** - Add more tasks |

Wait for approval before writing.

---

## Step 5: Write Files

### Generate IDs

```bash
# Epic ID from slug
# Example: EPIC-auth, EPIC-notifications

# Task IDs: EPIC-slug + number
# Example: TASK-auth-1, TASK-auth-2
```

### Write EPIC-\*.md

````markdown
---
id: EPIC-{slug}
status: open
priority: { from REQ or normal }
implements: REQ-{slug}
created: { date }
tasks:
  - TASK-{slug}-1
  - TASK-{slug}-2
  - TASK-{slug}-3
---

# {Title}

## Overview

{What this epic accomplishes}

## Approach

{High-level technical approach}
{Reference existing patterns: "Follow pattern at src/auth.ts:42"}

## Quick Commands

```bash
# Build
make build

# Test
make test

# Lint
make lint
```
````

## Acceptance

- [ ] All REQ criteria met
- [ ] Tests pass
- [ ] No lint errors

## References

- Requirement: REQ-{slug}
- {Other refs from research}

````

### Write TASK-*.md files

For each task:

```markdown
---
id: TASK-{slug}-N
status: todo
priority: normal
epic: EPIC-{slug}
blocked-by: [TASK-{slug}-X]  # or []
size: M
---
# {Task Title}

## Description
{What to build - WHAT not HOW. Describe the end-to-end behavior this vertical slice delivers.}

## Notes

- Blockers or open questions: {none | specific human decision/access/manual check needed}
- Out of scope: {adjacent behavior not included}

## Files
- `path/to/file.ts` - {what changes}
- `path/to/another.ts` - {what changes}

## Approach
{High-level approach}
{Reference patterns: "Follow pattern at src/example.ts:15"}

## Acceptance
- [ ] {specific observable criterion 1}
- [ ] {specific observable criterion 2}
- [ ] Success path test exists if code behavior changed
- [ ] Error or edge case test exists when relevant
- [ ] Tests pass
````

Use Write tool for each file.

---

## Step 6: Validate & Complete

```bash
specctl validate
specctl status
```

Show summary:

```
Created:
- EPIC-{slug} with {N} tasks
- Tasks: TASK-{slug}-1, TASK-{slug}-2, ...

Next steps:
1. Start work: /spec:work EPIC-{slug}
2. Review plan: Read .spec/epics/EPIC-{slug}.md
3. Refine tasks: /spec:interview TASK-{slug}-1
```

---

## The Golden Rule: No Implementation Code

Plans describe WHAT, not HOW.

**Allowed:**

- Signatures/interfaces
- Pattern references with file:line
- API notes from docs

**Forbidden:**

- Complete function implementations
- Copy-paste ready code (>10 lines)
- "Here's what you'll write" blocks

Implementation happens in `/spec:work`.

---

## Example Session

```
User: /spec:plan REQ-auth

Claude: [Reads REQ-auth]

Claude: [AskUserQuestion] "Should I explore the codebase first?"

User: Yes, quick scan

Claude: [Task Explore agent]

Claude: Based on the requirement and codebase research:

## Proposed Plan for REQ-auth

### Epic: EPIC-auth
OAuth authentication for Google and GitHub

### Tasks:
1. TASK-auth-1: Configure OAuth infrastructure
   - Size: S, Files: config/oauth.ts, .env.example
   - Blocked by: none

2. TASK-auth-2: Implement Google OAuth
   - Size: M, Files: auth/google.ts, routes/auth.ts
   - Blocked by: TASK-auth-1

3. TASK-auth-3: Implement GitHub OAuth
   - Size: M, Files: auth/github.ts, routes/auth.ts
   - Blocked by: TASK-auth-1 (can parallel with task 2)

4. TASK-auth-4: Add tests
   - Size: M, Files: __tests__/auth.test.ts
   - Blocked by: TASK-auth-2, TASK-auth-3

Does this plan look right?

User: Yes, create files

Claude: [Writes EPIC-auth.md, TASK-auth-1.md, etc.]

Created EPIC-auth with 4 tasks.
Next: /spec:work EPIC-auth
```

---

**Begin planning now.**
