---
name: linting-instructions
description: Lint plugin agent/skill prompts against rules derived from Anthropic model cards (Opus 4.6, Sonnet 4.6). Use when authoring or reviewing skills and agents — "lint instructions", "audit prompts", "model card rules".
user-invocable: true
context: fork
model: sonnet
allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash(uv run python scripts/lint-instructions.py*)
  - Agent
  - AskUserQuestion
---

# Instruction Lint (Model-Based Review)

Review agent and skill instructions against rules derived from the Claude Opus 4.6 and Sonnet 4.6 system cards. Combines a fast regex pre-pass with deep model-based semantic review. Do not fabricate compliance; report impossible or missing evidence directly.

---

## Step 1: Read the Rules

Read the lint rules rubric:

```
Read docs/instruction-lint-rules.md
```

This contains model-behavior and skill-structure rules:

- **Universal (U-\*)**: Apply to all agents/skills regardless of model
- **Opus-specific (O-\*)**: Address Opus 4.6's documented over-exploration and efficiency issues
- **Sonnet-specific (S-\*)**: Leverage Sonnet 4.6's documented steerability advantages
- **Skill structure (K-\*, I-\*)**: Check names, trigger descriptions, progressive disclosure, and sequential interaction

---

## Step 2: Run Regex Pre-Pass (optional baseline)

Run the fast regex linter for a structural baseline:

```bash
uv run python scripts/lint-instructions.py
```

Note which files have structural issues. These are heuristic — the model review in Step 3 is authoritative.

---

## Step 3: Model-Based Review

For each model tier, spawn a review agent that reads the actual instruction files and evaluates them semantically against the rules. The agent should understand INTENT, not just keyword presence.

**Parse `$ARGUMENTS`:**

- No args → review all plugins
- Plugin name (e.g., `go-dev`) → review only that plugin
- `opus` / `sonnet` / `haiku` → review only agents using that model

### Agent prompt template

For each batch of files, spawn an Agent with:

```
You are reviewing Claude Code plugin instructions for quality against
rules derived from the Opus 4.6 and Sonnet 4.6 system cards.

## Rules (apply based on model in frontmatter)

### Universal (all models)
- U-SCOPE: Must have clear scope boundaries (what's in, what's out)
- U-OUTPUT: Must define expected output format
- U-TOOL-FIRST: If agent has Bash, must require running tools before manual analysis
- U-FAILURE: Must handle failure/impossibility (prevents over-eager workarounds)
- U-GROUND: Must instruct to ground claims in actual tool output
- U-NO-DESTROY: If agent has Bash, must warn about destructive actions

### Opus agents (model: opus)
- O-EFFICIENCY: Must include efficiency constraints (Opus over-explores)
- O-SCOPE-ONLY: Should have "ONLY these" or "exclusively" markers
- O-EFFORT-MATCH: effort:high must be justified by complex multi-dimensional tasks

### Sonnet agents (model: sonnet)
- S-NO-LECTURE: Must NOT contain lecture-inducing patterns (Sonnet tends to lecture)
- S-DECISIVE: Should include decisive action language
- S-ANTI-EAGER: Should include anti-over-eagerness (Sonnet is steerable here)

### Skill structure
- K-NAME: Skill names should be kebab-case and clear
- K-DESC: Skill descriptions should include trigger language
- K-PROGRESSIVE: Large skills should use support files
- I-ONE-QUESTION: Interactive skills should ask sequentially

## Review these files

[list of file paths]

For each file:
1. Read it fully
2. Note the model from frontmatter
3. Apply the matching rules SEMANTICALLY — check intent, not just keywords
4. Rate each applicable rule: PASS / WARN / FAIL
5. For WARN/FAIL: explain specifically what's missing and suggest a fix
6. Prefer enriching existing skills over recommending new near-duplicates

## Output Format

For each file, output:

### `<relative path>` (model: <model>, kind: <agent|skill>)
| Rule | Verdict | Notes |
|------|---------|-------|
| U-SCOPE | PASS/WARN/FAIL | ... |
...

Then at the end, output a summary:
- Total files reviewed
- Pass/warn/fail counts per rule
- Top 5 most impactful improvements to make
```

### Batching strategy

<!-- CC-ONLY: begin -->

- Batch files by plugin (one agent per plugin)
- Launch agents in parallel where possible (up to 3 concurrent)
- Each agent reads its batch of files using Read tool
<!-- CC-ONLY: end -->

---

## Step 4: Aggregate and Present

Collect results from all review agents. Present:

1. **Summary table**: files x rules matrix
2. **Critical findings**: Any FAIL verdicts with specific fix suggestions
3. **Top improvements**: Ranked by impact (how many files affected x severity)
4. **Model-specific patterns**: Are opus agents missing efficiency guards? Sonnet agents missing anti-eagerness?

---

## Output

Present findings as a structured report:

```
## Instruction Lint Report

### Summary
- Files reviewed: N (X opus, Y sonnet, Z haiku)
- Regex pre-pass: N errors, N warnings
- Model review: N pass, N warn, N fail

### Critical Findings
1. ...

### Top 5 Improvements
1. ...

### Per-Plugin Results
...
```
