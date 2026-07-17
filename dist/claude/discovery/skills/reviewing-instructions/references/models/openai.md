# OpenAI Model Context

Use after `references/model-resolution.md` maps the target to OpenAI.

## Family guidance

- OpenAI models respond well to explicit roles, scope, tools, and output fields.
- Structured output is reliable when the schema or template is concrete.
- Complex reviews benefit from explicit step order and confidence reporting.
- Few-shot examples can help calibration, but only when they are short and task-matched.

## Scoring use

Apply universal, format, and skill-structure rules from `references/scoring-rubric.md`.
Do not apply Claude-only rules.
Do not assume exact GPT or o-series version behavior unless the file targets that model explicitly.

If the target is Codex backed by OpenAI, score the instruction text and harness constraints shown in the file; do not infer hidden Codex behavior.
