---
{"description":"Brainstorm ideas and stress-test draft plans before coding. Use when brainstorming, exploring approaches, designing a feature/API/flow, grilling or debating a bounded plan, challenging assumptions, or resolving design-blocking terminology. NOT for implementation task breakdown. NOT for generic technology comparisons or best-practice research; use researching-web. NOT for docs updates; use documenting-code.","name":"brainstorming-ideas"}
---
<!-- Pi platform guidance -->
<!-- Use installed Pi tool names exactly, including extension toolsets such as Task*, Monitor*, and Loop*. -->
<!-- When available, track work with Task* (`todo` is the fallback), run long or background commands with MonitorCreate, and schedule follow-up with LoopCreate instead of sleep/poll loops. -->


# Brainstorming Ideas

Turn a vague idea or draft plan into a chosen design before coding. Done when the
user has picked or deferred an approach knowing its trade-offs, the key decisions
and open questions are written down, and no implementation task list was produced.

## Session rules

- Ask one question at a time. Use the runtime's interactive question tool when one
  exists (single-select, multi-select, or free text) and always allow an Other
  answer. Without a tool, offer short labeled options plus Other.
- Read code and docs before asking what they can answer. Cite the paths that shape
  a recommendation.
- Give your recommendation with every question and every set of options.
- Cut speculative features at every step.

## Domain context

Before design questions, read whichever exist: `CONTEXT.md`, `CONTEXT-MAP.md`,
`docs/adr/`, and the nearest `*/CONTEXT.md` or `*/docs/adr/`. Use their terms.
Create or change them only with user approval, and only for a resolved term or
decision.

## Modes

- **Explore an idea.** If no topic was given, ask for one. Narrow until the problem
  fits one sentence: trigger, actor, what it builds on or replaces, non-goals, and
  the strongest constraint. State your assumptions and ask which are wrong. As soon
  as the problem is stated, propose 2-3 approaches, each with what it is, its
  trade-offs and risks, and when it wins; name the decision criteria that separate
  them and mark one recommendation. Refine the chosen design only as far as the
  problem needs (architecture, data flow, interface, error handling, testing),
  confirming with the user as you go.
- **Grill or debate.** A draft plan, a named trade-off such as "X vs Y", or a set
  of assumptions is already bounded; ask for a plan only when nothing concrete was
  named. For a named trade-off, lead with a side-by-side comparison and your take,
  grounded in the project's code; do not invent opposing positions. For a concrete
  plan, skip the comparison and go straight to `references/grill-protocol.md`: no
  rewritten plan.

Research external solutions only when the user asks for it. If the idea conflicts
with domain docs, quote the conflicting terms and resolve them first. If a
constraint blocks every approach, name the blocker and ask which one to relax.

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
