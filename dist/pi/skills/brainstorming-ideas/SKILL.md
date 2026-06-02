---
description: Brainstorm ideas and stress-test draft plans before coding. Use when
  brainstorming, exploring approaches, designing a feature/API/flow, grilling or debating
  a bounded plan, challenging assumptions, or resolving design-blocking terminology.
  NOT for implementation task breakdown; use spec-plan. NOT for generic technology
  comparisons or best-practice research; use researching-web. NOT for docs updates;
  use documenting-code or learning-patterns.
name: brainstorming-ideas
---

<!-- Pi platform guidance -->
<!-- Use Pi tool names exactly: read, bash, edit, write, ask_user_question, structured_output, todo, Agent, get_subagent_result, steer_subagent, web_search, web_answer, web_research. -->
<!-- Use Agent, get_subagent_result, and steer_subagent for delegated work. -->
<!-- Use ctx7 or npx ctx7@latest through bash when Context7 documentation lookup is required. -->

# Brainstorming Ideas

Turn a vague idea or draft plan into a well-formed design before coding.

## Core principles

- Ask one question at a time.
- Inspect code before asking when code can answer.
- Offer 2-3 options with trade-offs; mark one recommendation.
- Use existing `CONTEXT.md`, `CONTEXT-MAP.md`, and ADR vocabulary.
- Cut speculative features.

## Step 0: Load domain context

Before design questions, look for relevant project docs:

- `CONTEXT.md`
- `CONTEXT-MAP.md`
- `docs/adr/`
- nearest `*/CONTEXT.md` or `*/docs/adr/`

Read them when present. Use those terms in questions and designs. If no docs exist, create them only with user approval and only when a real term or decision is resolved.

## Step 1: Understand the idea

Ask: "What's the idea or plan you'd like to explore?"

Follow up one question at a time:

- What pain triggered this?
- Who uses it?
- What existing feature does it build on or replace?
- What is explicitly out of scope?

Stop when you can state the problem in one sentence.

## Step 2: Grill or debate a bounded plan when requested

Use this mode only for a specific plan or trade-off. If none is clear, ask for one.

Read `references/grill-protocol.md` and follow it. Also:

- Test assumptions with concrete edge cases.
- Flag vocabulary conflicts with `CONTEXT.md`.
- If the discussion turns into task breakdown, stop and route to `spec-plan`.

## Step 3: Surface requirements and assumptions

Use 5WH, skipping anything already clear:

1. WHO uses it?
2. WHY is it needed?
3. WHAT is the core capability?
4. WHERE does it live?
5. HOW should it work, if there is a strong constraint?

Then state assumptions explicitly and ask which are wrong.

## Step 4: Explore the codebase

Find:

- similar modules or flows
- conventions and testing patterns
- integration points
- constraints from ADRs or existing architecture

Summarize in 3-5 bullets. Use project vocabulary. Cite key paths when code shaped the recommendation.

## Step 5: Research external solutions only if requested

If the request is only a generic technology comparison or best-practice survey, use `researching-web` instead. Otherwise compare patterns, trade-offs, and common failure modes. Summarize before proposing approaches.

## Step 6: Propose approaches

Present 2-3 options. For each:

- **What**: one-sentence approach
- **Trade-offs**: complexity vs flexibility
- **Best when**: scenario where it wins

Mark one as recommended. Ask which fits best.

## Step 7: Detail the chosen design

Present only relevant ~200-word sections and confirm after each. Typical sections:

1. Architecture overview
2. Data flow
3. API or interface
4. Error handling
5. Testing strategy

Apply YAGNI at each section. Cut speculative pieces.

## Step 8: Capture outcome

If the outcome is more than a short answer, offer to write a concise design note:

```text
docs/plans/YYYY-MM-DD-<topic>-design.md
```

Include only: Problem, Chosen approach, Trade-offs, Open questions, Testing strategy.

If domain terms crystallized, propose a `CONTEXT.md` entry and write it only with user approval:

```markdown
Term:
One-sentence definition.
Avoid: overloaded synonym
```

If hard-to-reverse decisions crystallized, offer an ADR only when the decision is surprising without context and came from a real trade-off.

## Failure handling

- Idea conflicts with `CONTEXT.md` / `CONTEXT-MAP.md`: surface the contradiction explicitly ("the glossary defines X as A, this idea assumes B"). Resolve the term with the user before designing — do not silently pick one.
- A constraint blocks every approach: stop generating options. State the blocker, what would unblock it, and ask the user to relax the constraint or change scope.
- Idea is too vague to design (user cannot state the problem in one sentence): stay in Step 1. Ask one narrowing question at a time; do not fabricate requirements or jump to approaches.
- No bounded plan or trade-off exists for grill/debate mode: ask for one; do not invent opposing positions.

## Output format

```text
BRAINSTORM COMPLETE
===================
Topic: <topic>
Approach chosen: <name>
Design note: docs/plans/YYYY-MM-DD-<topic>-design.md or none

Key decisions:
- <decision>

Domain docs:
- <CONTEXT/ADR updates or none>

Open questions:
- <unresolved>
```
