# Instruction Scoring Rubric

Rubric version: 2026-06-03.

Use this file as the canonical scoring source for reviewing-instructions. Scores
stay in the 0-10 range, but scoring is band-first to reduce run-to-run drift.

## Scoring procedure

1. Confirm the file is agent-facing. If not, do not score it.
2. Apply hard gates and caps.
3. Score each dimension by choosing a band first.
4. Use the band midpoint unless concrete evidence supports the top or bottom of the band.
5. Compute the weighted score.
6. Apply caps again if needed.
7. Round to the nearest 0.5.
8. Assign confidence: high, medium, or low.

Band defaults:

- 0-2 band: default 1.
- 3-4 band: default 3.5.
- 5-6 band: default 5.5.
- 7-8 band: default 7.5.
- 9-10 band: default 9.5.

Use 0, 2, 3, 4, 5, 6, 7, 8, 9, or 10 only when the evidence clearly matches an edge. Avoid unsupported decimals inside dimensions.

## Weights

- Signal Density: 15 percent.
- Scope Specificity: 15 percent.
- Output Structure: 15 percent.
- Failure Handling: 15 percent.
- Format Efficiency: 10 percent.
- Grounding Discipline: 10 percent.
- Routing Precision: 10 percent.
- Progressive Disclosure: 10 percent.

## Hard gates and caps

Do not score:

- The file is not written for an AI agent or coding assistant.
- The file is ordinary source code, tests, generated output, or human-only docs.
- The review scope is too ambiguous to know what file is being judged.

Overall caps:

- Contradictory instructions that can cause unsafe or impossible behavior: maximum 6.
- Destructive or risky actions allowed without confirmation: maximum 5.
- No clear scope boundary for the main task: maximum 7.
- No output contract for a task that reports findings, plans, edits, or reviews: maximum 6.
- No failure handling: maximum 7.
- No evidence or grounding rule for review, audit, research, planning, or scoring tasks: maximum 7.
- Referenced required file is missing or unreadable: maximum 8.
- Unknown model context when model-specific behavior matters: maximum 8.
- Partial review due to missing linked files or unavailable tools: maximum 8.

Caps apply after dimension scores. If several caps apply, use the strictest cap.

## Confidence

High:

- Scope, model context, and linked files are clear.
- Scores cite direct evidence.
- No major tool or discovery gaps affected scoring.

Medium:

- One relevant context gap exists, but scores are still mostly grounded.
- Model family is clear but variant is unknown.
- Some linked files were not needed or could not be read.

Low:

- Scope is partial, model context is ambiguous, or linked files are missing.
- Several dimensions depend on inference.
- Subagent or repeated passes disagree by more than 1 point overall.

Low confidence is not a score penalty by itself. Use caps only when the gap affects review completeness.

## Dimension 1: Signal Density

Question: Would removing lines change model behavior?

0-2:

- Most content is generic advice, persona filler, tutorial prose, or repeated rationale.
- Many lines restate global rules the model already has.

3-4:

- Some useful constraints, but generic or repeated prose dominates important sections.
- Examples or rationale are long and not tied to decisions.

5-6:

- Mostly actionable, but 20-30 percent of lines are skippable.
- Several instructions describe obvious coding-agent defaults.

7-8:

- Tight operational guidance; at most 15 percent skippable.
- Most examples or rationale change decisions.

9-10:

- Nearly every line is a routing rule, behavioral constraint, workflow step, failure rule, or output contract.
- No filler.

## Dimension 2: Scope Specificity

Question: Does the file say when to use it and when not to use it?

0-2:

- Scope is absent or broad enough to justify unrelated work.

3-4:

- Positive scope exists, but exclusions and neighboring skills are missing.

5-6:

- Scope is understandable, but important boundaries are implied rather than explicit.

7-8:

- Clear in-scope and out-of-scope rules for the main task.
- Neighbor-skill overlap is mostly resolved.

9-10:

- Clear in/out scope, exit conditions, and routing to adjacent skills or roles.
- Ambiguous inputs have a stated handling path.

## Dimension 3: Output Structure

Question: Can the model produce the expected answer without guessing the format?

0-2:

- No output format.

3-4:

- Output type is named but structure is vague.

5-6:

- Required fields are described in prose, but no stable template exists.

7-8:

- Template or explicit field list covers normal output.

9-10:

- Exact template covers normal, partial, blocked, and no-finding outputs.
- Required fields and length or precision rules are clear.

## Dimension 4: Format Efficiency

Question: Does markdown formatting improve instruction following without visual noise?

0-2:

- Tables, diagrams, heavy bold, italic, or horizontal rules dominate.

3-4:

- One or two low-signal structures distract from the workflow, or bold appears on more than 30 percent of prose lines.

5-6:

- Mostly clean, but italic, horizontal rules, or bold overuse remain.

7-8:

- Uses headers, bullets, lists, and code blocks cleanly.
- Bold is sparse and meaningful.

9-10:

- Fully optimized for model parsing: clear headers, concise bullets, no tables, no diagrams, no italic, no horizontal rules, no bold overuse.

## Dimension 5: Failure Handling

Question: Does the file say what to do when normal execution fails?

0-2:

- No failure cases.

3-4:

- Vague fallback language without concrete triggers.

5-6:

- One or two common failures covered.

7-8:

- Most predictable failures have specific responses.

9-10:

- Missing input, ambiguous scope, unavailable tools, unsafe actions, impossible tasks, partial results, and verification failures are all covered.

## Dimension 6: Grounding Discipline

Question: Are claims tied to source text, tool output, or verification?

0-2:

- Conclusions can be asserted without evidence.

3-4:

- Grounding is encouraged but not required.

5-6:

- Evidence is required for some outputs but not all findings or scores.

7-8:

- Findings must cite file, section, line, or tool output.
- Missing evidence changes the result.

9-10:

- Strict evidence policy: no evidence, no finding.
- Verification or source reads are required before reporting success.

## Dimension 7: Routing Precision

Question: Will the description and name activate this file at the right time?

0-2:

- Name or description is generic, missing, or misleading.

3-4:

- Capability is described, but trigger language is missing.

5-6:

- Trigger phrases exist, but overlap with adjacent skills is unresolved.

7-8:

- Description includes use cases, exclusions, and common phrasing.

9-10:

- Unique activation context, strong trigger phrases, and explicit non-triggers.
- Platform-specific routing details do not leak into generic routing.

## Dimension 8: Progressive Disclosure

Question: Is the main file short enough while still pointing to needed detail?

0-2:

- Monolithic 300 or more lines, or trivial skill padded with reference material.

3-4:

- 220-300 lines with details that should move to references.

5-6:

- 150-220 lines and noticeably dense, or reference detail is inlined.

7-8:

- Main body is under 180 lines for skills or under 150 lines for agents.
- References are loaded conditionally.

9-10:

- Main body is focused, rare detail lives in named references, and read conditions are explicit.

## Skill-architecture heuristics

Use `references/skill-architecture.md` only for skill or agent instruction files
such as `SKILL.md`, `AGENT.md`, `body.md`, and agent-facing references loaded by
those entrypoints.

Map its heuristics into existing dimensions:

- Signal Density: no-op lines, duplicated meaning, sediment.
- Scope Specificity: branch ambiguity, thin-router scope, missing invocation boundary.
- Output Structure or Failure Handling: weak completion criteria, premature completion risk in step-based workflows.
- Grounding Discipline: weak legwork demand that lets the model skip evidence or verification.
- Routing Precision: invocation fit, one trigger per branch, synonym piles in descriptions.
- Progressive Disclosure: weak pointers to must-read support files, poor co-location, sprawl in the main file.

Do not score these heuristics separately. They are defect types and sub-checks,
not extra dimensions.

## Lint rule mapping

Universal rules:

- U-SCOPE: body contains scope-limiting language such as Do not, only, or explicit exclusions.
- U-OUTPUT: body defines an output section, template, findings structure, or required fields.
- U-FAILURE: body covers failure, unavailable tools, impossible work, skipped checks, or blocked states.
- U-GROUND: body requires evidence, actual file content, tool output, verification, or grounded claims.
- U-TOOL-FIRST: for tool-heavy files, commands appear before manual analysis instructions.
- U-NO-DESTROY: files with write or shell power warn before destructive actions.

Format rules:

- F-NO-TABLE: avoid markdown tables in instruction prose.
- F-NO-DIAGRAM: avoid mermaid and ASCII diagrams.
- F-NO-HR: avoid standalone horizontal rules outside frontmatter.
- F-NO-ITALIC: avoid italic emphasis.
- F-BOLD-SPARSE: bold on no more than 15 percent of prose lines.

Skill-structure rules:

- K-NAME: frontmatter name is clear kebab-case.
- K-DESC: frontmatter description includes trigger language such as Use when or Use for.
- K-PROGRESSIVE: long bodies use references instead of inlining detail.
- I-ONE-QUESTION: interactive files ask one question at a time.

Claude-only rules:

- O-EFFICIENCY: Opus-targeted files bound exploration and effort.
- O-SCOPE-ONLY: Opus-targeted files use strong scope-only language for narrow tasks.
- O-EFFORT-MATCH: high-effort Opus tasks have enough distinct focus areas to justify effort.
- S-NO-LECTURE: Sonnet-targeted files avoid instructions that invite lecturing the user.
- S-DECISIVE: Sonnet-targeted files include decisive action language.
- S-ANTI-EAGER: Sonnet-targeted files include anti-eagerness or ask-before-expanding rules.

## Lint status rules

PASS:

- Rule applies and evidence shows it is satisfied.

WARN:

- Rule applies, evidence is weak or partial, or the issue is low-risk.

FAIL:

- Rule applies and evidence shows a material gap that changes model behavior.

Not applicable:

- Rule does not apply to the file type, model, tools, or task.

## Score reporting

For each file, report:

- hard gates and caps
- dimension scores with evidence
- weighted overall score after caps
- confidence
- lint statuses grouped as PASS, WARN, FAIL, and not applicable when useful

If a second run differs by more than 1 point overall, compare hard gates and caps first. Most instability should be resolved there before adjusting dimension scores.
