---
model: haiku
allowed-tools: []
description: Quick methodology guide for spec-driven development
---

# Spec-Driven Development Guide

**Print this guide directly - no tools needed.**

---

## Output

```
╭──────────────────── SPEC-DRIVEN DEVELOPMENT ────────────────────╮
│                                                                 │
│         DESIGN ──────▶ PLAN ──────▶ IMPLEMENT                  │
│       /spec:interview  /spec:plan   /spec:work                 │
│       (requirements)   (tasks)      (code)                     │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│ PHASE 1: DESIGN (WHAT/WHY)                                      │
│   /spec:interview <idea>    Deep questioning → REQ-*.md         │
│   /spec:interview REQ-xxx   Refine existing requirement         │
│                                                                 │
│ PHASE 2: PLAN (HOW)                                             │
│   /spec:plan REQ-xxx        Create EPIC + vertical TASK files   │
│   /spec:plan EPIC-xxx       Refine existing epic                │
│                                                                 │
│ PHASE 3: IMPLEMENT                                              │
│   /spec:work                Start next ready task               │
│   /spec:work EPIC-xxx       Work on specific epic               │
│   /spec:work TASK-xxx       Work on specific task               │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│ OTHER COMMANDS                                                  │
│   /spec:init          Initialize .spec/ folder                  │
│   /spec:status        Show progress overview                    │
│   /spec:done TASK-xxx Mark task complete                        │
│   /spec:new task xxx  Create new task file                      │
│   /spec:help          This guide                                │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│ CLI HELPER (specctl)                                            │
│   specctl ready           Unblocked tasks in priority order     │
│   specctl start TASK-xxx  Mark task in_progress + start session │
│   specctl done TASK-xxx   Mark done with evidence + end session │
│   specctl reset TASK-xxx  Reset task back to todo               │
│   specctl validate        Check for issues (cycle detection)    │
│   specctl status          Progress overview                     │
│   specctl dep add A B     A depends on B (with cycle check)     │
│   specctl dep rm A B      Remove dependency                     │
│   specctl epic close X    Mark epic as done                     │
│   specctl hook install    Install git pre-commit validation     │
│   specctl session show    Show current session state            │
│   specctl session resume  Recovery info for interrupted work    │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│ FILE STRUCTURE                                                  │
│   .spec/                                                        │
│   ├── reqs/REQ-*.md      Requirements (WHAT) - from interview   │
│   ├── epics/EPIC-*.md    Epics grouping tasks                   │
│   ├── tasks/TASK-*.md    Vertical tasks with dependencies       │
│   ├── memory/            Pitfalls, conventions, decisions       │
│   ├── SESSION.yaml       Current session (task, step, commit)   │
│   └── PROGRESS.md        Activity log (last 10 entries)         │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│ KEY PRINCIPLES                                                  │
│   • REQ = WHAT/WHY (business requirements, success criteria)    │
│   • TASK = vertical slice with acceptance criteria              │
│   • Unresolved human decisions become blockers/open questions   │
│   • One task per session - complete before starting next        │
│   • Quality gates: make build && make test && make lint         │
│   • You approve every edit - no hidden automation               │
│                                                                 │
╰─────────────────────────────────────────────────────────────────╯

START HERE:
  No .spec/ folder? → /spec:init
  Have an idea?     → /spec:interview "your feature idea"
  Have REQ files?   → /spec:plan REQ-xxx
  Have TASK files?  → /spec:work
```

**Print this exactly as shown above.**
