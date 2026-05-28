# Instruction Review

Review AI agent and skill instruction files for quality. Combines a fast structural pre-pass with model-aware semantic scoring across 8 dimensions (0–10 each). Do not fabricate findings — cite exact file/section or missing evidence for every issue.

## Argument Parsing

From `$ARGUMENTS`:

- First non-flag token: file path, directory path, plugin name, or omitted (→ review all candidate instruction files)
- `--model <name>`: override model for rule selection (e.g. `--model claude`, `--model gpt-4o`)
- Plugin name without path separator → expand to `src/plugins/<name>/`

## File Discovery

Build the review set in this order:

1. Start with explicit instruction entrypoints: `SKILL.md`, `AGENT.md`, `AGENTS.md`, `CLAUDE.md`.
2. Expand to markdown those entrypoints tell the agent to read: platform-specific `body.md`, `references/*.md`, linked `.md` files, and named prompt/context/rules files.
3. Scan for other likely instruction markdown when the repo uses custom layouts. High-confidence signals:
   - file or path names such as `body.md`, `prompt*.md`, `instructions*.md`, `rules*.md`, `context*.md`, `policy*.md`
   - directories such as `agents/`, `skills/`, `prompts/`, `instructions/`, `references/`
   - frontmatter or metadata like `name:`, `description:`, `model:`, `tools:`, `allowed-tools:`
   - agent-directed content: imperative rules, tool guidance, output contracts, failure handling, `Use when`, `Do not`, `Read X.md`
4. Exclude ordinary docs like `README.md`, changelogs, product docs, and design docs unless an instruction file explicitly points to them or the file clearly addresses an AI agent.
5. If confidence is ambiguous, list the file under `Candidates Not Reviewed` with a short reason instead of forcing a score.

## Model Context Resolution

For each confirmed instruction file under review:

1. Check `--model` arg first; if absent, check the file's frontmatter `model:` field. Args take precedence.
2. If the file has no model metadata but is a support file, inherit model context from the parent instruction file when obvious.
3. Look for `references/models/<model>.md` in this skill's directory. Read it if present.
4. If no local reference: WebFetch the model's official prompting guide:
   - Claude: `https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/overview`
   - GPT series: `https://platform.openai.com/docs/guides/prompt-engineering`
   - Gemini: `https://ai.google.dev/gemini-api/docs/prompting-strategies`
   - Other: web search for `<model> prompting guide best practices`
5. If no model anywhere: read `references/models/generic.md`.

Surface the resolution as a one-line header in the report: `Model context: claude (from frontmatter)`.

## Step 1: Structural Pre-Pass

```bash
uv run python src/skills/reviewing-instructions/scripts/lint-instructions.py
```

If the script fails, record `skipped (script unavailable)` and continue with semantic review only.

Record which rule IDs flagged (U-SCOPE, K-DESC, F-NO-TABLE, etc.). The semantic review is authoritative.

## Step 2: Semantic Review and Scoring

Read `references/scoring-rubric.md` for 0–10 anchors and weights per dimension.

Spawn one review agent per plugin batch. Launch up to 3 in parallel:

```
Task(
  subagent_type="general-purpose",
  prompt="""
You are reviewing AI instruction files for quality.

Rules:
Read references/scoring-rubric.md for all lint rules, 0–10 anchors, and weights.
Read references/models/<model>.md for model-specific guidance (or references/models/generic.md if none).
Confirm each candidate file is meant to guide an AI agent. If confidence is low, move it to Candidates Not Reviewed instead of forcing a score.

Scoring dimensions:
1. Signal Density
2. Scope Specificity
3. Output Structure
4. Format Efficiency
5. Failure Handling
6. Grounding Discipline
7. Routing Precision
8. Progressive Disclosure

Files to review: [file paths]

For each file:
1. Read it fully.
2. Identify model from frontmatter or inherited parent context.
3. Score each dimension 0-10 with a one-line justification.
4. Apply lint rules — PASS / WARN / FAIL. For WARN/FAIL: cite exact section and propose a concrete fix.
5. Compute weighted overall score.
6. List top 3 improvements by impact.

Do not fabricate. "No evidence of X" is a valid finding.
""",
  run_in_background=True
)
```

## Step 3: Aggregate and Present

Collect all agent results. Output:

```
## Instruction Review Report

### Summary
- Files reviewed: N (model: M or generic)
- Extra instruction files discovered: N
- Candidates not reviewed: N
- Structural pre-pass: N errors, N warnings (or: skipped)
- Scores: mean X.X / 10 (range Y.Y–Z.Z)

### Scores

path/to/SKILL.md — overall 7.8 / 10
  Signal Density: 8 — most lines carry actionable constraints
  Scope Specificity: 6 — positive scope only; no exclusions stated
  Output Structure: 9 — template present with required fields
  Format Efficiency: 10 — no tables/diagrams/italic; clean
  Failure Handling: 5 — one failure case; missing exit conditions
  Grounding Discipline: 7 — grounding required in key steps
  Routing Precision: 8 — trigger phrases present; minor K-DESC gap
  Progressive Disclosure: 7 — 180 lines; borderline; consider splitting

### Critical Findings (FAIL)
1. path — U-SCOPE: no scope boundary. Fix: add "Do not X; review only Y."

### Top Improvements (by impact)
1. ...

### Candidates Not Reviewed
- path/to/file.md — why confidence was too low or why it was ordinary documentation

### Per-File Detail
...
```
