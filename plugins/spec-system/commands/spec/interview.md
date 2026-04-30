---
model: sonnet
description: Deep requirement gathering via structured questioning, domain language, out-of-scope checks, and PRD-quality requirements
argument-hint: <idea> | <doc-path> | REQ-xxx
allowed-tools:
  - AskUserQuestion
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash(specctl *)
  - Bash(mkdir *)
---

# Spec Interview

Deep requirement extraction through structured questioning. Creates comprehensive REQ-\*.md files.

**Role**: Requirements analyst
**Goal**: Extract complete requirements through structured questions, domain language alignment, and PRD-quality output in REQ-\*.md

## Input

$ARGUMENTS

**Input types:**

- **Idea text**: `"add OAuth login"` → Interview and create REQ-\*.md
- **Doc path**: `docs/auth-spec.md` → Read, interview, create REQ-\*.md
- **REQ ID**: `REQ-auth` → Read, interview, refine existing

If empty, ask: "What feature or requirement would you like to explore?"

---

## Step 1: Detect Input & Load Context

### If REQ ID (starts with REQ-)

```bash
specctl show $INPUT 2>/dev/null
```

If found, read the file. Interview to refine.

### If file path (contains / or ends with .md)

Read the file. Use content as starting context.

### If idea text

Start fresh interview.

---

## Step 2: Interview Process

**CRITICAL**: Use AskUserQuestion tool for EVERY question.

- DO NOT output questions as text
- Ask one question per AskUserQuestion call
- Usually ask 8-15 questions; go longer only for genuinely complex requirements
- Stop when success criteria, scope, constraints, and blockers are clear

### Before Questions: Load Durable Context

Read relevant project docs when present:

- `CONTEXT.md` / `CONTEXT-MAP.md` — domain language
- `docs/adr/*.md` — architectural decisions
- `.out-of-scope/*.md` — rejected enhancements

If the new requirement resembles an `.out-of-scope/` record, surface it before continuing: "This resembles a previously rejected concept because X. Reconsider, narrow scope, or stop?"

Use the domain vocabulary from `CONTEXT.md`. If the user uses an overloaded term, resolve it before writing the REQ.

### Question Categories

Ask in this order, adapting based on answers:

#### 1. Problem & Scope (5-8 questions)

- What problem does this solve?
- Who experiences this problem?
- How painful is this problem today? (workarounds?)
- What's in scope vs explicitly out of scope?
- Is this a new capability or improving existing?

#### 2. Users & Stakeholders (4-6 questions)

- Who are the primary users?
- Who are secondary users (admin, support, etc.)?
- What do users need to accomplish?
- How do they accomplish this today?
- Any accessibility requirements?

#### 3. Success Criteria (5-8 questions)

- What does "done" look like?
- How will users know it works?
- What would make users happy vs delighted?
- Any performance requirements (speed, scale)?
- Any compliance or regulatory requirements?

#### 4. Constraints (4-6 questions)

- Technical constraints (must use X, can't use Y)?
- Business constraints (timeline, budget, dependencies)?
- Compatibility requirements (browsers, devices, APIs)?
- Security requirements (auth, data protection)?

#### 5. Edge Cases & Failures (6-10 questions)

- What happens if [input] is invalid?
- What if user is offline/disconnected?
- What if external service is down?
- What if user cancels mid-operation?
- What are the error states?
- How should errors be communicated?
- Any rate limiting or abuse concerns?

#### 6. Data & State (4-6 questions)

- What data is needed?
- Where does data come from?
- What happens to existing data?
- Any data retention/deletion requirements?
- Privacy considerations?

#### 7. Unknowns & Risks (3-5 questions)

- What are you most uncertain about?
- What could derail this?
- What needs research first?
- Any dependencies on other work?

### Interview Guidelines

1. **Ask NON-OBVIOUS questions** - Assume technical competence
2. **Dig deep on answers** - Follow up on interesting points
3. **Surface hidden complexity** - Ask about things user might not have considered
4. **Probe contradictions** - If answers don't align, clarify
5. **Use multiSelect** for non-exclusive options
6. **Stop when complete** - Don't pad with unnecessary questions

---

## Step 3: Write REQ-\*.md

After interview complete, create/update requirement file.

### Generate REQ ID

If new requirement:

```bash
# Find next available number
existing=$(ls .spec/reqs/REQ-*.md 2>/dev/null | wc -l | tr -d ' ')
# Use descriptive suffix from the topic
# Example: REQ-auth, REQ-notifications, REQ-export
```

### REQ File Template

```markdown
---
id: REQ-{slug}
version: 1
priority: { critical|normal|low }
created: { date }
---

# {Title}

## Problem

{Clear problem statement from interview}

## Users

- **Primary**: {who}
- **Secondary**: {who, if any}

## Success Criteria

- [ ] {criterion 1}
- [ ] {criterion 2}
- [ ] {criterion 3}

## Constraints

- {constraint 1}
- {constraint 2}

## Edge Cases

- {edge case 1}: {expected behavior}
- {edge case 2}: {expected behavior}

## Data Requirements

- {what data is needed}
- {where it comes from}

## Open Questions

- {unresolved items needing research}

## Implementation Decisions

- {modules/interfaces likely touched, if known}
- {technical constraints or decisions already made}

## Testing Decisions

- {critical behaviors to test}
- {public interfaces or integration seams to verify}
- {edge/error cases that matter}

## Out of Scope

- {explicitly excluded items}

## Domain Language

- {terms resolved or added to CONTEXT.md}

## Prior Decisions and Rejections

- {relevant ADRs or .out-of-scope records}
```

### Write the file

```bash
mkdir -p .spec/reqs
```

Then use Write tool to create `.spec/reqs/REQ-{slug}.md`

If refining existing REQ, use Edit tool to update sections.

---

## Step 4: Completion

Show summary:

- Questions asked: {count}
- Key decisions captured
- Out-of-scope items captured
- Domain terms resolved
- File written: `.spec/reqs/REQ-{slug}.md`

Suggest next step:

```
Requirement captured. Next steps:
1. Create implementation plan: /spec:plan REQ-{slug}
2. Refine further: /spec:interview REQ-{slug}
3. View status: /spec:status
```

---

## NOT in scope (defer to /spec:plan)

- File/line references
- Task creation
- Task sizing (S/M/L)
- Implementation approach
- Dependency ordering

Interview captures WHAT/WHY. Plan captures HOW.

---

## Example Session

```
User: /spec:interview "add user notifications"

Claude: [AskUserQuestion] "What type of notifications?"
  - Email only
  - In-app only
  - Both email and in-app
  - Push notifications too

User: Both email and in-app

Claude: [AskUserQuestion] "What triggers a notification?"
  - User actions (comments, mentions)
  - System events (jobs complete, errors)
  - Scheduled (daily digest)
  - All of the above

... 35 more questions ...

Claude: Created .spec/reqs/REQ-notifications.md

Next: /spec:plan REQ-notifications
```

---

**Begin interview now. Use AskUserQuestion for every question.**
