# OpenAI GPT-5.5 Model Context

Applies to GPT-5.5 and GPT-5.5 Pro agents/skills (codename "Spud", released 2026-04-23). Context window: 1.1M tokens. Default reasoning effort: medium.

## Behavioral traits

- Strong instruction following: explicit, direct instructions are effective. Ambiguity handled well but boundaries still help.
- No documented over-exploration tendency (unlike Claude Opus). Scope guards improve precision but are less critical.
- XML tags not required — role-based messages (system/user/assistant) are the native format.
- Few-shot examples work well. Structured output via `response_format` is reliable.
- Reasoning effort is configurable (`none` / `low` / `medium` / `high` / `xhigh`). Instructions for complex analysis benefit from noting this in context.

## Rules to apply

All rules are in `references/scoring-rubric.md`. Apply universal (U-prefix), format (F-prefix), and skill-structure (K-prefix) rules. Do NOT apply O-prefix or S-prefix rules — those are Claude-only.

## Prompting best practices (GPT-5.5)

- System prompt is effective; put role, scope, and output format there.
- Describe tools clearly in the system prompt for tool-heavy workflows.
- For complex multi-step review, consider noting `reasoning_effort: high` in context if the platform exposes it.
- Verbosity still hurts: over-specified instructions cause rule amnesia just as with Claude.
- Output format templates work well — GPT-5.5 pattern-matches reliably against structure.
