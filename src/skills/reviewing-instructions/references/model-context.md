# Model Context

Read when the target names a model family or the user passes `--model`. Model
context adds findings; it never overrides caps or the evidence rule.

When the model-guidance skill is installed, use it to resolve a specific model
and read its verified prompting guidance. This file stays at family level on
purpose: version-level advice goes stale fast.

## Resolution

Use the first match:

- `--model <name>` from the user.
- `model` in the target sidecar (`.agentbundler/targets/<target>.json`
  `frontmatterPatch`) or in the file's own frontmatter.
- The target the file renders for: Claude → Anthropic, Codex → OpenAI,
  Grok → xAI. Pi, Copilot, and Cursor run many models → generic.
- The parent entrypoint, for support files.
- Generic.

A base `SKILL.md` or agent file ships to every target, so its default context is
generic. Report `Model context: <family or generic> — source <arg|sidecar|target|parent|generic>`.
An unknown alias resolves to generic; report the alias and set confidence to
medium.

## Family aliases

- Anthropic: `claude`, `anthropic`, `opus`, `sonnet`, `haiku`, `fable`, `mythos`,
  and IDs starting with `claude-`.
- OpenAI: `openai`, `gpt`, `codex`, and IDs starting with `gpt-` or an o-series
  prefix.
- xAI: `xai`, `grok`, and IDs starting with `grok-`.
- Generic: no metadata, unknown aliases, or mixed-model files.

## Family guidance

Anthropic:

- Thinking is adaptive and effort is a setting. Flag think-harder exhortations
  and requests to write out internal reasoning.
- State the result and what done means rather than every intermediate step.
- For research or analysis, ask it to mark what it could not confirm and where
  it looked.
- Prompts that worked on the previous generation are the baseline; change them
  only where evaluation shows a gap.

OpenAI:

- Keep instructions concise and consistent. Procedural rules written for smaller
  tiers can over-constrain the flagship tier.
- State the result, the completion boundary, and which ambiguities need a
  question; otherwise it may stop at a first pass or ask too often.
- Specify length and structure when they matter; it tends toward long,
  formatted answers.
- Calibrate verification: once required checks pass, repeat them only after a
  change or failure. Repeated demands to verify produce redundant checks.

xAI:

- Reasoning effort is a setting; prompts need no think-harder text.
- Published prompting guidance is thin. Score with the universal rubric and say
  that model-specific confidence is limited.

Generic:

- Apply the universal rubric only. Lower confidence rather than guess when a
  model-specific issue is likely.
