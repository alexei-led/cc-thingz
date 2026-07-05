---
description: Brainstorm ideas and stress-test draft plans before coding. Use when
  brainstorming, exploring approaches, designing a feature/API/flow, grilling or debating
  a bounded plan, challenging assumptions, or resolving design-blocking terminology.
  NOT for implementation task breakdown. NOT for generic technology comparisons or
  best-practice research; use researching-web. NOT for docs updates; use documenting-code.
name: brainstorming-ideas
---

<!-- Pi platform guidance -->
<!-- Use installed Pi tool names exactly. Installed extensions may add toolsets such as Task*, Monitor*, and Loop*; use the visible tool names exactly and do not translate them to Claude syntax. -->
<!-- Prefer Task* over `todo` when task-tracking tools are available; `todo` is the cc-thingz fallback. Prefer MonitorCreate for long-running background commands and LoopCreate for scheduled or event-driven follow-up instead of Bash sleep/poll loops. -->
<!-- Use subagent for delegated work. Use wait to block on async subagent runs only when no independent work remains. -->
<!-- Use ctx7 or npx ctx7@latest through bash when Context7 documentation lookup is required. -->

# Brainstorming Ideas

Turn a vague idea or draft plan into a well-formed design before coding. Keep the
session collaborative, question-driven, and small enough to change direction.

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
- User stops mid-session: offer the paused output or a short design note.
