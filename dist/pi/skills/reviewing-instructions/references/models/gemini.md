# Gemini Model Context

Use after `references/model-resolution.md` maps the target to Gemini.

## Family guidance

- Gemini handles long context well, but concise scoped instructions still improve reliability.
- Markdown headings and explicit step order work well.
- Put task constraints before large context when possible.
- Short examples can help output consistency when the file's task has a repeated format.

## Scoring use

Apply universal, format, and skill-structure rules from `references/scoring-rubric.md`.
Do not apply Claude-only rules.
Do not reward examples just because Gemini can use them; examples should change task behavior or calibrate output.

If Pro versus Flash is unknown, use family guidance only and lower confidence when reasoning depth affects the score.
