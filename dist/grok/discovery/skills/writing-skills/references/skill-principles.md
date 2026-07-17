# Skill Principles

Use these rules when the shape of the skill matters, not just its wording.

## Goal

A good skill makes the agent take a predictable process. It does not need to
produce identical text every run. It must route cleanly, do the right legwork,
and stop at a clear finish line.

## Invocation

Choose invocation mode on purpose.

Model-invoked:

- Use when the agent should find the skill on its own.
- Use when another skill may need to route to it.
- Cost: the description stays loaded and competes with other skills.

User-invoked:

- Use when the skill is a manual expert tool, a niche reference, or a router.
- Cost: the user has to remember it exists.

Do not split a skill into two model-invoked skills unless each one has a real,
independent trigger surface.

## Description rules

The description is trigger text, not a summary paragraph.

- Start with the main action or noun the user will say.
- Keep one trigger per branch.
- Collapse synonym piles into one strong phrase.
- Name neighboring skills only when overlap is real.
- Put the NOT-clause in the description when misuse is likely.
- Do not spend description tokens on body detail, examples, or rationale.

A description should answer two questions fast:

1. When should this skill fire?
2. When should it not?

## Information hierarchy

Keep the common path at the top and push optional detail down.

Inline in `SKILL.md`:

- scope
- workflow steps
- output contract
- failure handling
- rules every run needs

Move to `references/`:

- examples
- long checklists
- domain detail
- alternate branches that only some runs need
- glossary or comparison material

Move to target overlays only when the base cannot stay vendor-neutral.

## Split only when the boundary is real

Split a skill when one of these is true:

- the trigger surface is different enough that one description would blur routing
- the later steps pull the agent into premature completion of the current step
- a large body really contains two separate workflows

Do not split for:

- style preference
- tiny wording differences
- duplicate references that can stay behind separate pointers
- imagined future specialization

## Prune aggressively

Check each line against these tests:

- Does it change behavior?
- Does it belong in this file instead of a reference?
- Does another line already own this meaning?

Delete lines that are:

- generic agent advice
- repeated constraints
- pretty prose without operational effect
- stale references to removed tools or old repo structure

## Common failure modes

Routing overlap:

- The skill and a neighbor trigger on the same phrasing.
- Fix the description and NOT-clause before changing the body.

Sprawl:

- The body is long even though most lines are still live.
- Move branch-specific detail to references.

Duplication:

- The same rule appears in description, body, and references.
- Keep one source of truth.

No-op prose:

- The line restates what a decent coding agent already does.
- Replace it with a concrete constraint or delete it.

Premature completion:

- The workflow tells the agent to do broad work but never says what done looks
  like.
- Sharpen the completion point or split the workflow.

## Finish line

A skill is ready when:

- its description has a distinct trigger surface
- its body keeps only common-path rules
- its optional detail lives behind explicit pointers
- its output contract is concrete when the task needs one
- its failure handling covers the predictable misses
