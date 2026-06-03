# Calibration Anchors

Use this file only when a score is borderline, confidence is low, or the user asks
for reranking. Match the reviewed file to the closest anchor, then adjust only
when evidence clearly supports it.

## Anchor: 10

Pattern:

- Clear use and do-not-use scope.
- Exact output contract with normal, blocked, and partial-result cases.
- Strong failure handling and evidence rules.
- Main file is short; references are loaded conditionally.
- No format lint issues.

Score:

- Overall 9.5 or 10.
- Confidence high.

## Anchor: 8

Pattern:

- Scope, output, failure handling, and grounding are present.
- One area is weaker, such as missing neighbor-skill routing or partial failure cases.
- Minor format or progressive-disclosure issues do not change behavior much.

Score:

- Overall 7.5 or 8.
- Confidence high or medium.

## Anchor: 6

Pattern:

- Main workflow is useful, but one hard gate is weak.
- Examples: positive scope without exclusions, prose output with no exact template, or grounding only implied.
- The model can probably perform the task, but results vary by run.

Score:

- Overall 5.5 or 6.
- Apply caps when the gate rules require them.

## Anchor: 4

Pattern:

- Several core behaviors are missing or conflicting.
- The file mixes routing, implementation, and reference material without clear order.
- Output shape is guessed by the model.

Score:

- Overall 3.5 or 4.
- Confidence medium unless evidence is very clear.

## Anchor: 2

Pattern:

- Not enough task guidance to perform reliably.
- Mostly generic persona or motivational prose.
- Unsafe, contradictory, or impossible instructions dominate.

Score:

- Overall 1 or 2.
- If not agent-facing, do not score instead.

## Pairwise rerank rule

When comparing two instruction files or two versions of one file:

1. Apply hard gates to both.
2. Compare each dimension as A better, B better, or tie.
3. Use caps to prevent a polished but unsafe file from winning.
4. Prefer the file with stronger scope, output, failure handling, and grounding when totals are close.
5. If the score difference is less than 0.5 and evidence is similar, call it a tie.

## Repeated-run stability rule

If repeated runs differ:

- Difference up to 0.5: treat as scoring noise.
- Difference from 1 to 1.5: compare gates, caps, and confidence.
- Difference greater than 1.5: rerun with calibration anchors and exact same scope.

Do not average runs that used different scopes, model contexts, or rubric versions.
