# Instruction Scoring Rubric

Rubric version: 2026-09-28.

The canonical scoring source for reviewing-instructions. It rewards instructions
that state the result and the finish line, say each rule once, keep hard
constraints explicit, and leave the rest to the model. The writing-skills skill
teaches the same style to authors.

## Procedure

- Confirm the file is agent-facing. Do not score source code, tests, generated
  output, human-only docs, or a scope too ambiguous to name the file.
- Score each dimension by choosing a band first, then its default. Move to a band
  edge (0, 2, 3, 4, 5, 6, 7, 8, 9, 10) only when the evidence clearly matches it.
- Compute the weighted score, apply caps, and round to the nearest 0.5.
- Assign confidence.

Band defaults: 0-2 → 1, 3-4 → 3.5, 5-6 → 5.5, 7-8 → 7.5, 9-10 → 9.5.

## Evidence

This rule governs the reviewer, not the reviewed file: every score and finding
cites a section, line, or exact quote, or names the missing text. No evidence,
no finding. A reviewed file does not need its own evidence, failure, or output
sections unless its task produces output another tool or agent parses.

## Weights

- Outcome and Done: 20 percent.
- Routing: 15 percent.
- Consistency: 15 percent.
- Hard Constraints: 15 percent.
- Concision: 15 percent.
- Progressive Disclosure: 10 percent.
- Portability: 10 percent.

## Caps

- Contradictory instructions that can cause unsafe or impossible behavior: maximum 6.
- Destructive, irreversible, or outward-facing action (secrets, prod apply,
  deletes, publishing, releases) allowed without a confirmation gate: maximum 5.
- A required referenced file is missing or unreadable: maximum 8.
- Partial review because linked files or tools were unavailable: maximum 8.

When several caps apply, use the strictest.

## Confidence

- High: scope and linked files are clear, and every score cites direct evidence.
- Medium: one context gap, such as an unread optional reference or an unknown
  target, but scores are still mostly grounded.
- Low: partial scope, several dimensions rest on inference, or repeated passes
  disagree by more than 1 point.

Low confidence is not a penalty. Use a cap only when the gap affects completeness.

## Dimension 1: Outcome and Done

Does the file state the result, the constraints, and what "done" means, and
leave the path to the model?

- 0-2: No stated result; the file is a persona, a tutorial, or a list of tips.
- 3-4: The result is implied. Long numbered procedures prescribe steps whose
  order is not a real constraint.
- 5-6: The result is stated, but done is vague ("verify", "make sure it works"),
  or verification is demanded repeatedly.
- 7-8: Result and a testable done criterion are stated once. Steps appear only
  where order matters.
- 9-10: The same, plus when to ask versus proceed is explicit, and a consumed
  output shape is specified when another tool or agent parses it.

## Dimension 2: Routing

Will the name and description load the file at the right time?

- 0-2: Name or description is generic, missing, or misleading.
- 3-4: Says what it does but not when to use it.
- 5-6: Says what and when, but overlap with neighbors is unresolved.
- 7-8: What, when, and NOT-for with named neighbor skills.
- 9-10: The same, one trigger per branch, no synonym piles, no body detail in the
  description, and target-only routing kept out of the base.

## Dimension 3: Consistency

Is each rule stated once, with no conflict inside the file, with its overlays, or
with neighboring skills?

- 0-2: Rules conflict, or the same rule appears three or more times.
- 3-4: The body restates the description's NOT-for list, or verification and
  final-response boilerplate repeats across sections.
- 5-6: A few duplicates or one minor conflict.
- 7-8: Each rule appears once; references extend rather than repeat the body.
- 9-10: The same, and the file agrees with its overlays and with the neighbors it
  names.

## Dimension 4: Hard Constraints

Are the constraints that must not bend explicit, short, and placed where they
apply?

- 0-2: Risky actions (secrets, destructive commands, prod apply, releases,
  external actions) appear with no limit.
- 3-4: Limits exist but are buried, vague, or diluted among many soft rules.
- 5-6: Limits are clear, but preferences are also phrased as prohibitions, so
  the real limits do not stand out.
- 7-8: Hard limits are short and explicit, negative where that is clearest;
  preferences are positive statements.
- 9-10: The same, and each limit names its approval or stop point.

Files with no risky capability score this dimension by whether they add false
limits. A read-only reviewer with no constraint noise scores 7-8.

## Dimension 5: Concision

Would removing lines change behavior?

- 0-2: Mostly generic advice, textbook method, persona, or motivation.
- 3-4: Model-known material ("read the code first", language idioms, what a test
  is) dominates important sections, or emphasis inflation (ALL-CAPS, "MANDATORY",
  "think step by step") appears.
- 5-6: 20-30 percent of lines are skippable.
- 7-8: At most 15 percent skippable. What remains is local, non-obvious,
  opinionated, version-gated, or costly to rediscover.
- 9-10: Nearly every line changes a decision. Headers, lists, and code blocks carry
  structure; a table appears only where it is the clearest form.

## Dimension 6: Progressive Disclosure

Does the main file keep the common path and point to detail at the right moment?

- 0-2: A monolith over 500 lines, or a trivial skill padded with reference detail.
- 3-4: 350-500 lines with branch-specific detail that belongs in references.
- 5-6: Under 350 lines, but references lack read-when conditions, or support
  files chain to further support files.
- 7-8: Well under 500 lines; each reference is one level deep with a stated
  reason to read it.
- 9-10: The same, and deterministic operations live in scripts rather than
  prose.

## Dimension 7: Portability

Does the file work on every target it ships to?

- 0-2: The base depends on one vendor's tools, tokens, or agent body to function.
- 3-4: Target-only tokens (argument substitution, vendor tool names, MCP tool
  IDs) sit in the base, or the file links into another skill's files.
- 5-6: The base is neutral, but it names specific model versions or assumes a
  role body that other targets do not load.
- 7-8: Neutral base, self-contained, other skills named rather than linked;
  target additions live in overlays.
- 9-10: The same, and overlays patch named sections; a whole-body replace is
  used only for a deliberate full fork.

## Defect labels

Use these as finding sublabels when they sharpen the diagnosis:

- `no-op` — restates default model behavior.
- `duplication` — one meaning in more than one place.
- `conflict` — two rules that cannot both hold.
- `over-prescription` — ordered steps where order is not a constraint.
- `emphasis` — ALL-CAPS, "MANDATORY", or think-harder exhortations.
- `sediment` — stale text about removed tools, paths, or models.
- `sprawl` — the main file is too long even when most lines are live.
- `thin-router` — mostly delegates without independent capability.
- `weak-pointer` — must-read detail exists, but nothing says when to read it.

## Finding severity

- High: causes wrong, unsafe, or unroutable behavior.
- Medium: costs tokens or routing accuracy on every run.
- Low: polish.

## Stability

- Round-to-round difference up to 0.5 is noise.
- Difference of 1-1.5: compare caps and confidence first.
- Difference over 1.5: rescore with `references/calibration.md` on the same scope.

Do not average runs with different scopes, model contexts, or rubric versions.
