---
allowed-tools:
- AskUserQuestion
- Task
- TaskCreate
- TaskUpdate
- TaskList
- Read
- Grep
- Glob
- Write
- Edit
- mcp__perplexity-ask__perplexity_ask
- WebFetch
- Bash(git status *)
- Bash(git log *)
- Bash(git diff *)
- Bash(git show *)
argument-hint: '[idea|plan|grill|debate] <topic-or-plan>'
context: fork
description: Brainstorm ideas and stress-test draft plans before coding. Use when
  brainstorming, exploring approaches, designing a feature/API/flow, grilling or debating
  a bounded plan, challenging assumptions, or resolving design-blocking terminology.
  NOT for implementation task breakdown. NOT for generic technology comparisons or
  best-practice research; use researching-web. NOT for docs updates; use documenting-code.
name: brainstorming-ideas
user-invocable: true
---

# Brainstorming Ideas

Follow the base skill. This Claude overlay only defines tool use and platform-specific behavior.

## Claude tool rules

- Use `AskUserQuestion` for every choice point. Do not write numbered menus and ask the user to type `1`, `2`, or `3`.
- Ask one question per `AskUserQuestion` call.
- Use single-select for one path, multi-select for multiple risks/constraints/goals, and `allowOther` for custom answers.
- Use `TaskCreate` and `TaskUpdate` to track phases when the session has more than two steps.
- Use `Read`, `Grep`, and `Glob` before asking questions that the repo can answer.
- Use `Write` or `Edit` only after the user approves the exact design note, CONTEXT entry, or ADR target.
- Use external research tools only after the user chooses research or asks for it.

## Suggested interactive questions

Initial question:

- Header: `Idea type`
- Question: `What would you like to brainstorm?`
- Options: New feature, Modification, Integration, Plan grill/debate, Exploration
- Allow Other: yes

Assumptions check:

- Header: `Assumptions`
- Question: `Which assumptions are wrong or risky?`
- Options: All correct, Some wrong, Not sure, Defer this
- Allow Other: yes

Next-step checkpoint:

- Header: `Next step`
- Question: `How should we proceed?`
- Options: Explore codebase, Research solutions, Explore then research, Skip to approaches
- Allow Other: yes

Approach choice:

- Header: `Approach`
- Question: `Which approach fits best?`
- Options: Recommended option, alternative option, minimal/YAGNI option
- Allow Other: yes

Design validation:

- Header: `Validate design`
- Question: `Does this section look right?`
- Options: Yes continue, Needs changes, Go back, Stop here
- Allow Other: yes

Implementation handoff:

- Header: `Next steps`
- Question: `What should happen next?`
- Options: Create worktree, Create plan, Save design note, Done for now
- Allow Other: yes

## Optional exploration

If the user chooses codebase exploration, run a bounded read-only scan. Prefer direct `Read`/`Grep`/`Glob`; use a subagent only for broad scans.

Prompt shape for a broad scan:

```text
Quick scan only. Find project structure, relevant flows, conventions, integration points, and tests for: <idea>. Return 5 bullets with file paths. Do not edit.
```

If no relevant code appears, say `no prior implementation found`; do not fabricate patterns.

## Optional research

If the user chooses research, use Perplexity or WebFetch with a scoped query. Summarize sourced patterns before proposing approaches. If live retrieval is unavailable, say so and continue from local context only.

## Capture rules

- For `CONTEXT.md` entries, ask for approval of the exact one-sentence definition before editing.
- For ADRs, require all three: hard to reverse, surprising without context, and a real trade-off.
- For design notes, write only concise Problem, Chosen approach, Trade-offs, Open questions, and Testing strategy.

## Failure handling

- If the user asks for task sequencing, state that it is outside this skill's scope.
- If the user asks for generic technology research, route to `researching-web`.
- If the user asks for docs-only work, route to `documenting-code`.
- If the user stops mid-session, offer `BRAINSTORM PAUSED` or a short design note.

### Execute this collaborative brainstorming workflow now
