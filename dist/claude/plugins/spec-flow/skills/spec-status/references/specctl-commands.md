# specctl commands (bundled CLI)

CLI at `scripts/specctl`.

- `scripts/specctl init` — create the `.spec/` structure
- `scripts/specctl ready [--epic EPIC-x]` — list unblocked tasks, priority order
- `scripts/specctl show <REQ-x | EPIC-x | TASK-x>` — render an artifact
- `scripts/specctl start TASK-x` — mark in-progress, record base commit
- `scripts/specctl done TASK-x --summary ... --files ... --commits ... --tests ...` — close with evidence
- `scripts/specctl validate` — check for orphans, cycles, missing fields
- `scripts/specctl status` — global counts and progress
- `scripts/specctl dep add A B [--type X]` — add dependency with cycle check
- `scripts/specctl dep rm A B` — remove dependency
- `scripts/specctl epic close X` — mark an epic done
- `scripts/specctl session show | resume | step <name>` — session state and recovery
- `scripts/specctl hook install` — install git pre-commit validation
