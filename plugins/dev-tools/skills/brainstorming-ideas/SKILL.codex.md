---
name: brainstorming-ideas
description: Brainstorm ideas and stress-test draft plans before coding. Use when brainstorming, exploring approaches, designing a feature/API/flow, grilling a plan, challenging assumptions, or resolving terminology that blocks the design. NOT for implementation task breakdown; use /spec:plan. NOT for general documentation updates; use documenting-code or learning-patterns.
---

# Brainstorming Ideas

Turn a vague idea or draft plan into a well-formed design. Ask one question at a time. If the answer is discoverable from code, inspect code instead of asking.

## Core principles

- One question at a time.
- YAGNI at every step.
- Present design in small sections and confirm before continuing.
- Propose 2-3 concrete options with trade-offs.
- Use project domain language from `CONTEXT.md` / `CONTEXT-MAP.md` when present.
- Offer ADRs only for hard-to-reverse, surprising, real trade-off decisions.

## Step 0: Load domain context

Before design questions, look for relevant project docs:

- `CONTEXT.md`
- `CONTEXT-MAP.md`
- `docs/adr/`
- nearest `*/CONTEXT.md` or `*/docs/adr/`

Read them when present. Use those terms in questions and designs. If no docs exist, create them lazily only when a real term or decision is resolved.

## Step 1: Understand the idea

Ask: "What's the idea or plan you'd like to explore?"

Follow up one question at a time:

- What pain triggered this?
- Who uses it?
- What existing feature does it build on or replace?
- What is explicitly out of scope?

Stop when you can state the problem in one sentence.

## Step 2: Grill the plan when requested

If the user passed `plan`, `grill`, or asked to challenge/stress-test a plan, walk the decision tree. Keep it focused on design quality and assumptions, not implementation task breakdown; use `/spec:plan` for tasks.

For each question:

- Provide your recommended answer.
- Explain why the branch matters.
- Inspect code instead of asking when possible.
- Flag vocabulary conflicts with `CONTEXT.md`.
- Use concrete edge-case scenarios.

When a domain term is resolved, propose a tight `CONTEXT.md` entry:

```markdown
**Term**:
One-sentence definition.
_Avoid_: overloaded synonym
```

Offer an ADR only when all three are true:

1. Hard to reverse.
2. Surprising without context.
3. Result of a real trade-off.

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

Summarize in 3-5 bullets. Use project vocabulary.

## Step 5: Research external solutions only if requested

Compare patterns, trade-offs, and common failure modes. Summarize before proposing approaches.

## Step 6: Propose approaches

Present 2-3 options. For each:

- **What**: one-sentence approach
- **Trade-offs**: complexity vs flexibility
- **Best when**: scenario where it wins

Mark one as recommended. Ask which fits best.

## Step 7: Detail the chosen design

Present ~200-word sections and confirm after each:

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

If domain terms or decisions crystallized, update `CONTEXT.md` or create a short ADR only with user approval.

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
