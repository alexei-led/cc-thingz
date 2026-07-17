# Generic Model Context

Use when no model family is known or when model-specific rules do not apply.

## Stable guidance

- Specific scope and concrete output contracts improve instruction following.
- Short, structured instructions are more reliable than broad narrative guidance.
- Evidence requirements reduce hallucinated findings and scores.
- Failure handling prevents fabricated completion when inputs or tools are missing.
- Progressive disclosure keeps common workflow in the main file and rare detail in references.

## Scoring use

Apply universal, format, and skill-structure rules from `references/scoring-rubric.md`.
Do not apply vendor-only rules.

If generic context hides a likely model-specific issue, keep the score grounded in universal rules and lower confidence rather than guessing.
