# Skill Architecture Heuristics

Use this file only when the review target is a skill or agent instruction file:
`SKILL.md`, `AGENT.md`, `body.md`, or agent-facing references loaded by them.

## Goal

Judge predictability first.

A strong skill makes the agent follow the same process every run. Do not reward
style, vocabulary, or extra prose unless it changes routing or execution.

## Invocation fit

Check whether the invocation mode earns its cost.

- A model-invoked skill keeps a description loaded all the time. That cost must
  buy autonomous discovery or cross-skill routing.
- A niche reference, manual expert tool, or thin wrapper may be a better
  user-invoked skill.
- A thin router is a warning sign: it mostly delegates or restates a neighbor
  without enough independent capability.

Map these findings to Routing Precision, Scope Specificity, or Progressive
Disclosure. Do not create a separate score.

## Description as trigger surface

The description is trigger text, not a summary paragraph.

Check for:

- one trigger per branch
- synonym piles that restate one branch several ways
- body detail or rationale leaking into the description
- missing NOT-clauses when adjacent skills overlap
- trigger wording that does not match how users or nearby skills actually ask

Map these findings to Routing Precision.

## Information hierarchy

Check whether the main file keeps only the common path.

Inline in the main file:

- scope
- core workflow
- output contract
- failure handling
- rules every run needs

Push down into references or overlays:

- branch-specific detail
- examples
- long checklists
- glossary material
- target-specific behavior

Review the pointer, not just the target:

- if a support file is required, the entrypoint must say when to read it
- weak pointer wording can hide must-read detail just as badly as missing detail
- definitions, rules, and caveats that belong together should stay co-located

Map these findings to Progressive Disclosure, Signal Density, or Scope
Specificity.

## Workflow soundness

Use this pass only for files with steps or ordered workflow.

Check for:

- completion criteria the agent can test
- premature completion risk, where later steps pull the agent forward before the
  current step is truly done
- weak legwork demand, where the wording lets the agent skip reading,
  verification, or evidence collection

Map these findings to Output Structure, Failure Handling, or Grounding
Discipline.

## Failure-mode labels

Use these as finding sublabels when they sharpen the diagnosis:

- `no-op` — instruction restates default model behavior
- `duplication` — the same meaning appears in more than one place
- `sediment` — stale or irrelevant leftover text
- `sprawl` — the main file is too long even when most lines are live
- `thin-router` — mostly delegates without enough independent capability
- `weak-pointer` — must-read support detail exists but the entrypoint does not
  reliably send the agent there

These labels explain the defect type. They do not replace evidence, gates, caps,
or the main dimensions.
