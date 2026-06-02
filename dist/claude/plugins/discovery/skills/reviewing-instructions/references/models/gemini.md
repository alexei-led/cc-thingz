# Gemini Model Context

Applies to Gemini 2.5 Pro and Gemini 2.5 Flash agents/skills used via Gemini CLI. Context window: 1M input tokens, 64K output.

## Behavioral traits

- Always-on thinking: reasoning cannot be disabled on Gemini 2.5 Pro. Thinking budget is dynamic by default — let it self-pace on complex review tasks.
- Default temperature 1.0 — do not lower arbitrarily. Lowering temperature on thinking models causes looping or degraded performance.
- XML tags and Markdown headings both effective for prompt structure. Prefer Markdown headers for instruction files; XML tags for delineating context vs task sections.
- Put context first, question last for long-context tasks: "Based on the information above, [question]".
- Few-shot examples improve output quality — include 2–3 varied examples with consistent formatting.

## Rules to apply

All rules are in `references/scoring-rubric.md`. Apply universal (U-prefix), format (F-prefix), and skill-structure (K-prefix) rules. Do NOT apply O-prefix or S-prefix rules — those are Claude-only.

## Prompting best practices (Gemini)

- Be precise and direct: state goals clearly; avoid unnecessary persuasive framing.
- Put constraints and role definitions at the start or in the system prompt.
- For multi-step review: chain tasks explicitly or instruct step-by-step — the model handles complex reasoning well but benefits from explicit sequencing.
- Verbosity still hurts: over-specified instructions reduce instruction-following reliability, same as with other frontier models.
- Output format templates work reliably — Gemini pattern-matches well against concrete structure.
