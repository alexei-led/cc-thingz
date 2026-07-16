# Model Resolution

Resolve model context before scoring. Model context selects extra rules; it does
not override universal gates, caps, or evidence requirements.

## Resolution order

1. User argument: `--model <name>`.
2. File frontmatter: `model`, `thinking`, target metadata, or platform folder.
3. Parent entrypoint for support files.
4. Target directory such as claude, codex, pi, or openai.
5. generic.

Report the source in the review header.

## Alias map

Claude family:

- claude, anthropic, opus, sonnet, haiku.
- claude-opus, claude-sonnet, claude-haiku.
- anthropic model IDs that contain opus, sonnet, or haiku.

OpenAI family:

- openai, gpt, gpt-4, gpt-4o, gpt-5, o1, o3, o4.
- openai model IDs that start with gpt or o.
- codex agents backed by OpenAI models.

Generic:

- no model metadata
- unknown aliases
- mixed-model files without a primary target

## Variant rules

Claude:

- Apply universal Claude guidance for family claude.
- Apply Opus rules only when the variant is explicit or model ID contains opus.
- Apply Sonnet rules only when the variant is explicit or model ID contains sonnet.
- Apply Haiku handling only when the variant is explicit or model ID contains haiku.

OpenAI:

- Apply OpenAI family guidance for gpt, o-series, and codex-backed OpenAI models.
- Do not assume exact version behavior unless the file states a version or the model ID is explicit.

Generic:

- Apply universal rules only.
- Set confidence medium when model-specific behavior could change the score.

## Failure handling

- Unknown alias: use generic, report the alias, and set confidence medium or low.
- Conflicting metadata: prefer explicit user argument, then file frontmatter, then parent.
- Missing local model reference: use generic and report the missing reference.
- Vendor docs unavailable: do not block scoring; use local references and report the gap.
- Model-specific rule conflicts with project instruction policy: project instruction policy wins.
