# Capture learnings (Step 6)

After completion, optionally record a lesson or follow-up task.

## Recording a note

- Pitfall or convention → `.spec/memory/`
- Domain term → `CONTEXT.md` (user approves wording)
- Rejected enhancement → `.out-of-scope/<concept>.md`

## Filing a discovered task

- Ask the user to describe it, then use the `spec-new` skill: `spec-new task <slug>`.
- Link back: `scripts/specctl dep add TASK-<new-slug> TASK-<id> --type discovered-from`.
