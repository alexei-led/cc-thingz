# spec-system

Spec-driven development: structured requirements, vertical-slice tasks, and evidence-based completion workflows. Agent and commands are Claude Code-only; Codex CLI users get the spec-planner agent's knowledge via skills.

## Commands (8)

| Command           | Purpose                                              |
| ----------------- | ---------------------------------------------------- |
| `/spec:init`      | Initialize `.spec/` or add reqs from docs            |
| `/spec:interview` | Deep requirement gathering with domain/out-of-scope checks |
| `/spec:plan`      | Create EPIC + vertical-slice TASK files                           |
| `/spec:work`      | Main loop: select → plan → implement → verify → done       |
| `/spec:status`    | Progress overview (`--list`, `--todo`, `--check`)    |
| `/spec:new`       | Create new task or requirement                       |
| `/spec:done`      | Mark complete (`--discover`, `--verify`)             |
| `/spec:help`      | Methodology quick reference                          |

## Agents (1)

- `spec-planner` (sonnet) — creates implementation plans with style learning

## CLI Tool

`specctl` provides quick queries without entering a slash command:

```bash
specctl status              # Progress overview
specctl status --json       # Machine-readable status
specctl ready               # Next tasks (priority-ordered)
specctl session resume      # Recovery info after interruption
specctl session handoff     # End-of-session summary
specctl dep list TASK-xxx   # Show task dependencies
specctl validate            # Check for issues
```

## `.spec/` Structure

```
.spec/
├── reqs/           # REQ-*.md — WHAT (success criteria, constraints)
├── epics/          # EPIC-*.md — grouping tasks
├── tasks/          # TASK-*.md — HOW (implementation steps)
├── memory/         # pitfalls.md, conventions.md, decisions.md
├── SESSION.yaml    # Current session state (auto-managed)
└── PROGRESS.md     # Auto-managed activity log (last 5 entries)
```

## Workflow

`/spec:init` → `/spec:work` (repeats) → `/spec:done`

Each `/spec:work` cycle: select a task → plan implementation → implement → verify → mark done.

## MCP Servers

| Server              | Used For                        |
| ------------------- | ------------------------------- |
| Sequential Thinking | Systematic task decomposition   |
| MorphLLM            | Codebase search during planning |
