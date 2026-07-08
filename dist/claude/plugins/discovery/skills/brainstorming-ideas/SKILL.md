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

## Core rules

- Ask one question at a time.
- Use an interactive question tool when available; do not emulate menus in plain text.
- Inspect code before asking when code can answer.
- Offer 2-3 options with trade-offs and mark one recommendation.
- Always allow a free-text or Other answer when options may not fit.
- Cut speculative features and keep implementation task breakdown out of scope.

## Interactive questions

When a runtime question tool is available, use it for every choice point:

- single-select for one path, approach, or confirmation
- multi-select for multiple goals, risks, constraints, or audiences
- free text for problem statements, plan details, or custom answers
- options plus Other when you can suggest likely answers but need flexibility

Do not ask the user to type `1`, `2`, or `3` unless no interactive tool is
available. If no tool exists, use concise labeled options and include `Other`.

## Load domain context

Before design questions, look for relevant project docs:

- `CONTEXT.md`
- `CONTEXT-MAP.md`
- `docs/adr/`
- nearest `*/CONTEXT.md` or `*/docs/adr/`

Read them when present. Use those terms in questions and designs. If no docs
exist, create them only with user approval and only when a real term or decision
is resolved.

## Understand the idea

If the user did not supply a topic or plan, ask what they want to explore. Then
narrow one question at a time until you can state the problem in one sentence.
Prefer questions about:

- pain or trigger
- user or actor
- existing feature it builds on or replaces
- explicit non-goals
- strongest constraint

## Grill or debate mode

Use only for a bounded plan, trade-off, or assumption. If none is clear, ask for
one. Read `references/grill-protocol.md` and follow it.

Stay focused on design quality and assumptions, not implementation task breakdown.
If the user asks for task sequencing, state that it is outside this skill's scope.

## Surface requirements and assumptions

Use 5WH, skipping what is already clear:

1. WHO uses it?
2. WHY is it needed?
3. WHAT is the core capability?
4. WHERE does it live?
5. HOW should it work, only when a hard constraint exists?

State assumptions explicitly and ask which are wrong or risky. Use multi-select
when several assumptions can be wrong.

## Explore context before solutions

Find similar modules, flows, conventions, integration points, test patterns, and
architecture constraints. Summarize in 3-5 bullets. Cite key paths when code
shaped the recommendation.

Research external solutions only if the user asks or selects that path. If the
request is only a generic technology comparison or best-practice survey, use
`researching-web` instead.

## Propose and validate approaches

Present 2-3 approaches. For each:

- What: one-sentence approach
- Trade-offs: complexity vs flexibility
- Best when: scenario where it wins

Mark one recommendation. Ask which fits best with the interactive question tool.

Then detail the chosen design in short sections, confirming after each:

1. Architecture overview
2. Data flow
3. API or interface
4. Error handling
5. Testing strategy

Apply YAGNI at each section. Remove pieces that do not solve the stated problem.

## Capture outcome

If the outcome is more than a short answer, offer to write a concise design note:

```text
docs/plans/YYYY-MM-DD-<topic>-design.md
```

Include only Problem, Chosen approach, Trade-offs, Open questions, and Testing strategy.

If a domain term crystallized, propose a `CONTEXT.md` entry and write it only with
user approval:

```markdown
Term:
One-sentence definition.
Avoid: overloaded synonym
```

Offer an ADR only for decisions that are hard to reverse, surprising without
context, and came from a real trade-off.

## Output contracts

Completed:

```text
BRAINSTORM COMPLETE
Topic: <topic>
Approach chosen: <name or none>
Design note: <path or none>
Key decisions: <bullets>
Domain docs: <updates or none>
Open questions: <bullets or none>
```

Paused or routed:

```text
BRAINSTORM PAUSED | ROUTED TO <skill>
Topic: <topic>
Current state: <one sentence>
Resolved: <bullets>
Needed next: <question, artifact, or target skill>
```

## Failure handling

- Idea conflicts with domain docs: quote the conflicting terms and resolve with the user before designing.
- A constraint blocks every approach: state the blocker, what would unblock it, and ask what to relax.
- Idea is too vague: stay in understanding mode; ask one narrowing question at a time.
- No bounded plan exists for grill/debate: ask for one; do not invent opposing positions.
- If the user asks for task sequencing, state that it is outside this skill's scope.
- If the user asks for generic technology research, route to `researching-web`.
- If the user asks for docs-only work, route to `documenting-code`.
- If the user stops mid-session, offer `BRAINSTORM PAUSED` or a short design note.

### Execute this collaborative brainstorming workflow now

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
