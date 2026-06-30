---
description: 'Use when asked to lint, audit, review, or score AI-facing instruction
  files such as SKILL.md, AGENT.md, AGENTS.md, CLAUDE.md, platform body.md files,
  prompt files, rules, policies, and agent-facing references. NOT for plugin manifests,
  application code review, harness configuration review, ordinary docs, tests, or
  generated build output.

  '
name: reviewing-instructions
---

# Instruction Review

Review AI-facing instruction files for routing precision, behavioral signal,
output contracts, failure handling, grounding, and score stability. Do not score
ordinary docs or source code.

## Read first

- `references/scoring-rubric.md` for gates, 0-10 bands, caps, confidence, and output schema.
- `references/model-resolution.md` for model alias mapping and fallback rules.
- `references/skill-architecture.md` only when reviewing `SKILL.md`, `AGENT.md`, `body.md`, or agent-facing references loaded by them.
- `references/calibration.md` only when a score is borderline or confidence is low.
- `references/models/<family>.md` only after model family resolution.

## Accepted inputs

The user may pass:

- file path, directory path, or plugin name
- omitted scope, meaning discover likely instruction files
- `--model <name>` to override model family or variant
- requests such as lint, audit, review, score, compare, or rerank

A name without a path separator expands to matching `src/skills/<name>` or
`src/agents/<name>`. If it matches `src/plugins/<name>`, use `plugin.yaml`
only as routing evidence for agent-facing markdown or prompt files when the user
explicitly asks for instruction scoring. Route plugin manifest review to
`evolving-config`.

## Scope boundaries

Review only markdown or prompt files that guide an AI agent or coding assistant.
Include support files only when an entrypoint tells the agent to read them or when
they live under that skill or agent folder. For plugins, score only agent-facing
markdown or prompt files; never score `plugin.yaml`.

Do not review:

- application source code, tests, or generated artifacts
- ordinary README, changelog, product, or design docs unless agent-facing
- plugin or package manifests such as `src/plugins/*/plugin.yaml`; use `evolving-config`
- harness config quality; use evolving-config
- code quality; use reviewing-code

If a candidate is ambiguous, put it in Candidates Not Reviewed with the reason.

## Discovery

Build the review set in this order:

1. Explicit paths from the user.
2. Entrypoints: SKILL.md, AGENT.md, AGENTS.md, CLAUDE.md.
3. Support files referenced by entrypoints: body.md, references, prompt, rules, context, and policy markdown.
4. High-confidence agent-facing markdown in agents, skills, prompts, instructions, references, or rules directories.

For a single explicit file, review that file only unless the user asks for linked files.
For a directory, include its entrypoint and local support files.
If scope is omitted and discovery would likely expand past one skill, one agent, or one plugin, ask one clarifying question before step 4.

## Model resolution

Use `references/model-resolution.md`.

Resolution order:

1. `--model <name>` from the user.
2. File frontmatter model or platform metadata.
3. Parent entrypoint model for support files.
4. Tool or target folder family when obvious.
5. generic.

Report one line per review set: `Model context: <family>/<variant or generic> — source <arg|frontmatter|parent|folder|generic>`.

If resolution is ambiguous, use generic and set review confidence to medium or low.

## Structural pre-pass

Run the lint script scoped to the review target when Bash is available:

```bash
uv run python src/skills/reviewing-instructions/scripts/lint-instructions.py <scope>
```

If scope is omitted and broad review was not explicitly confirmed, ask one
clarifying question before any whole-repo pre-pass.
If scope is omitted and broad review is confirmed, run the whole-repo pre-pass.
If the script ignores scope, filter reported findings to reviewed files before
scoring.

If the script fails or is unavailable, record `Structural pre-pass: skipped` with
the exact reason and continue semantic review.

The pre-pass is advisory. Semantic review and the scoring rubric are authoritative.

## Semantic review

For each confirmed file:

1. Read the file fully.
2. Confirm it is agent-facing.
3. Resolve model context.
4. If the file is a skill or agent instruction file, load `references/skill-architecture.md` and map its heuristics into the existing dimensions. Do not create a separate score.
5. Apply hard gates from the scoring rubric.
6. Score each dimension using band-first 0-10 anchors.
7. Apply caps and confidence rules.
8. Rate applicable lint rules as PASS, WARN, or FAIL.
9. List the top 1-3 improvements by impact.

Use evidence for every score and finding: section name, line number, exact text,
or missing evidence. No evidence, no finding.

## Scoring stability rules

- Choose the rubric band first, then choose the midpoint unless evidence justifies an edge.
- Apply caps before computing the final score.
- Round final scores to the nearest 0.5.
- Use low confidence instead of over-precise scoring when context is partial.
- Do not let one polished section hide a missing hard gate.
- For repeated scoring or reranking, use the same scope, model context, and rubric version.

## Output

```markdown
## Instruction Review Report

Model context: <family/variant> — source <source>
Rubric version: <date or file path>
Review confidence: high | medium | low

### Summary

- Files reviewed: N
- Candidates not reviewed: N
- Structural pre-pass: <errors/warnings or skipped reason>
- Score range: X-Y / 10
- Main risk: <one sentence>

### Scores

path/to/file.md — overall X / 10, confidence <high|medium|low>

- Gates: pass | capped at N because <reason>
- Signal Density: X — <evidence>
- Scope Specificity: X — <evidence>
- Output Structure: X — <evidence>
- Format Efficiency: X — <evidence>
- Failure Handling: X — <evidence>
- Grounding Discipline: X — <evidence>
- Routing Precision: X — <evidence>
- Progressive Disclosure: X — <evidence>
- Lint: PASS <ids>; WARN <ids>; FAIL <ids>

### Findings

1. path — <severity> <rule or dimension[/subtype]>: <issue>. Evidence: <section/line/text>. Fix: <concrete fix>.

### Top Improvements

1. <highest-impact change>
2. <next change>
3. <next change>

### Candidates Not Reviewed

- path — <reason>
```

Omit empty optional sections. If no findings remain after evidence checks,
`No confirmed findings.` replaces only the Findings section; Summary and per-file
Scores with evidence remain required.

## Failure handling

- Missing scope and broad discovery or whole-repo lint would be expensive: ask one clarifying question before proceeding.
- Unknown model alias: use generic, report the alias gap, and lower confidence.
- Vendor docs unavailable: use local model reference or generic; do not block review.
- Conflicting local and vendor guidance: local project rules win; report the conflict.
- Parallel or delegated reviews disagree: apply the same gates and caps, then keep the lower-confidence result out of confirmed findings.
