---
{"description":"Brainstorm ideas and stress-test draft plans before coding. Use when brainstorming, exploring approaches, designing a feature/API/flow, grilling or debating a bounded plan, challenging assumptions, or resolving design-blocking terminology. NOT for implementation task breakdown. NOT for generic technology comparisons or best-practice research; use researching-web. NOT for docs updates; use documenting-code.","name":"brainstorming-ideas"}
---

# Brainstorming Ideas

Turn a vague idea or draft plan into a chosen design before coding. Done when the
user picks or defers an approach with its trade-offs known, decisions and open
questions recorded, and no implementation task list produced.

## Session rules

- Do not implement or change files until the user explicitly approves that scope.
- Ask one question at a time, with a recommendation. Use the runtime's
  interactive question tool when available (single-select, multi-select, or
  free text) or short labeled options otherwise; always include an Other choice.
- Read code and docs before asking what they answer; cite the paths that shape
  a recommendation.
- Cut speculative features at every step.

## Domain context

Before design questions, read whichever exist: `CONTEXT.md`, `CONTEXT-MAP.md`,
`docs/adr/`, and the nearest `*/CONTEXT.md` or `*/docs/adr/`. Use their terms, and
create or change them only with user approval, for a resolved term or decision.

## Modes

- **Explore an idea.** Compare two or three viable approaches against the goal
  and strongest constraints. State the assumptions that affect the trade-offs,
  recommend one approach, and ask only the next question that could change the
  decision. If there is no topic, ask for one.
- **Grill or debate.** A draft plan, a named trade-off such as "X vs Y", or a set
  of assumptions is already bounded; ask for a plan only when nothing concrete was
  named. For a named trade-off, lead with a side-by-side comparison and your take,
  grounded in the project's code, then continue into `references/grill-protocol.md`'s
  resolve-or-defer loop through GRILL COMPLETE; do not invent opposing positions.
  For a plan or an assumption set, skip the comparison and go straight to
  `references/grill-protocol.md`: no rewritten plan.

Research externally only when asked. If the idea conflicts with domain docs, quote
and resolve the conflicting terms first. If a constraint blocks every approach,
name it and ask which to relax.

## Capture the outcome

When the result is more than a short answer, offer a design note at
`docs/plans/YYYY-MM-DD-<topic>-design.md` with only Problem, Chosen approach,
Trade-offs, Open questions, and Testing strategy.

If a domain term crystallized, propose a `CONTEXT.md` entry and write it only with
user approval:

```markdown
Term:
One-sentence definition.
Avoid: overloaded synonym
```

Offer an ADR only for a decision that is hard to reverse, surprising without
context, and the result of a real trade-off.

## Output

```text
BRAINSTORM COMPLETE | BRAINSTORM PAUSED
Topic: <topic>
Approach chosen: <name or none>
Key decisions: <bullets>
Open questions: <bullets or none>
Design note: <path or none>
Domain docs: <updates or none>
```

## Platform additions

No target-specific additions.
