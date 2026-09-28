# Skill Principles

Read when the shape of a skill matters, not just its wording: invocation mode,
splits and merges, and pruning.

## Invocation fit

- Model-invoked: the agent or another skill must find it unprompted. Cost: the
  description stays loaded every session and competes with every other skill.
- User-invoked: a manual expert tool, niche reference, or router. Cost: the user
  has to remember it exists.
- A thin router that mostly delegates or restates a neighbor does not earn a
  loaded description. Fold it into the owner or make it user-invoked.

## Description

The description answers what the skill does, when to use it, and when not to.

- Lead with the action or noun the user will say.
- One trigger per branch; collapse synonym piles into one strong phrase.
- Name the neighbor skill in a NOT-for clause when misuse is likely.
- Keep body detail, examples, and rationale out of it.
- Match how users and nearby skills actually phrase the request.

## Information hierarchy

Inline in `SKILL.md`: the result, the done line, hard constraints, and rules
every run needs.

Move to `references/`, each with a read-when condition in `SKILL.md`: branch
detail, examples, long checklists, per-language or per-platform detail, and
glossary or comparison material.

Move to a target overlay only what the vendor-neutral base cannot say.

Keep definitions, rules, and caveats that belong together in one place. A weak
pointer hides must-read detail as badly as a missing one.

## Split, merge, or extend

Split when the trigger surfaces differ enough that one description would blur
routing, or when one body holds two separate workflows. Do not split for style,
small wording differences, or imagined future needs.

Prefer, in order: tighten the existing skill, move detail to references, add a
small target overlay, create a new skill.

## Prune

For each line ask: does it change behavior, does it belong here rather than in
a reference, and does another line already own this meaning? Delete generic
agent advice, repeated constraints, prose without operational effect, and stale
references to removed tools, paths, or models.

