# Claude Model Context

Use after `references/model-resolution.md` maps the target to Claude.

## Family guidance

- Claude follows explicit scope and output contracts well.
- Ambiguous broad tasks can trigger over-exploration; narrow scope and stop conditions help.
- Short rationale can help with critical constraints, but long explanation hurts signal density.
- Tool-grounded instructions and evidence requirements reduce unsupported claims.

## Variant rules

Opus:

- Check for effort bounds on narrow tasks.
- Check for strong scope-only language when the task should not expand.
- High-effort settings should match genuinely complex, multi-dimensional work.

Sonnet:

- Check for anti-eagerness language when the task is bounded.
- Check that the file avoids lecture-inducing instructions.
- Decisive action language is useful for implementation or review workflows.

Haiku:

- Prefer explicit step order and concrete output fields.
- Do not require extra Claude-only rules beyond universal scoring unless the file targets Haiku directly.

## Scoring use

Apply universal, format, and skill-structure rules to all Claude files.
Apply Opus, Sonnet, or Haiku variant rules only when the variant is explicit.
If the file says only Claude, use family guidance and keep variant-specific rules not applicable.
