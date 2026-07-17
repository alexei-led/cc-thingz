# Apply Fixes

Load this file only when the user explicitly asks for fixes or passes `--fix`.
Review-only requests must stop after the audit report.

## Approval gate

If fixes were not already approved, ask one question:

- Action: apply which fixes? Options: critical only, critical and important, selected items, show diffs only, skip.

Ask a second confirmation before risky changes. Name the files and risk. Risky
changes include permissions, sandbox policy, hooks, MCP servers, model routing,
package installs, deletes, moves, broad rewrites, private config, and managed
settings.

## Fix rules

- Edit source files, not generated exports.
- Apply only approved findings. Do not include opportunistic cleanup.
- Prefer small `edit` changes over rewrites.
- Keep secrets redacted.
- Show a concise diff summary.
- Run the closest validation command for touched config.

## If validation fails

Revert the fix unless the user asks to keep it. Quote the failing line or command
output and state the next safe action.
