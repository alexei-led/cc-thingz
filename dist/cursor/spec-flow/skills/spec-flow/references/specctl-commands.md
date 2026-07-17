# specctl commands

Bundled CLI: `scripts/specctl`.

## Core loop

- `scripts/specctl init` — create `.spec/` folders.
- `scripts/specctl new task <slug|topic/slug>` — create a task template.
- `scripts/specctl new req <slug|topic/slug>` — create a requirement template.
- `scripts/specctl ready [--epic EPIC-x]` — list unblocked `todo` tasks.
- `scripts/specctl start TASK-x` — set a task `in-progress` and open `SESSION.yaml`.
- `scripts/specctl checkpoint [--message "..."]` — append progress and print handoff.
- `scripts/specctl session handoff` — print resume summary with git diff/status.
- `scripts/specctl done TASK-x --summary ... --tests ... [--files ...] [--commits ...]` — close with evidence.

## Inspect and repair

- `scripts/specctl status [id] [--json]` — overview or one artifact summary.
- `scripts/specctl show <REQ-x|EPIC-x|TASK-x>` — print artifact markdown.
- `scripts/specctl validate` — check IDs, status, refs, cycles, and task quality.
- `scripts/specctl reset TASK-x` — reset to `todo`; clears matching active session.
- `scripts/specctl dep add TASK-b TASK-a` — make `TASK-b` wait for `TASK-a`.
- `scripts/specctl dep add TASK-b TASK-a --type discovered-from` — add an informational discovery link.
- `scripts/specctl dep rm TASK-b TASK-a` — remove a blocker.
- `scripts/specctl dep list TASK-b` — list task links.
- `scripts/specctl session show|resume|clear|step <name>` — inspect or update active session.

`specctl done` requires `--summary` and `--tests` unless `--force` is used. If checks were skipped, write the reason in `--tests`, for example `--tests "not run: docs-only task"`.
