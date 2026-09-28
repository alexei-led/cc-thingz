# Apply Fixes

Read only in fix mode: the user asked for changes or passed `--fix`.

## Approval

If fixes were not already approved, ask one question: apply which fixes —
critical only, critical and important, selected items, show diffs only, or skip.

Before any risky change listed under Limits in `SKILL.md`, confirm again and
name the files and the risk.

## Applying

- Apply only approved findings; leave opportunistic cleanup for a later audit.
- Prefer small edits over rewrites, and keep secrets redacted.
- Show a short diff summary and run the closest validation for the touched
  config.
- If validation fails, revert the change unless the user asks to keep it, quote
  the failing line, and state the next safe action.
