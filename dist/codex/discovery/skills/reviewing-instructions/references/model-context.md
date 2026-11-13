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
- The parent entrypoint, for support files.
- Generic. A target or harness does not establish the provider or model: Pi,
  Claude Code, and other clients can use routers or alternative providers.

A base `SKILL.md` or agent file ships to every target, so its default context is
generic. Report `Model context: <family or generic> — source <arg|sidecar|parent|generic>`.
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

Family names alone do not establish a release's prompting behavior, controls,
or deployment. Apply the universal rubric; use a resolved model's documented
guidance only where relevant. Lower confidence rather than guess when a
model-specific issue is likely. Keep API controls and conversation state in the
host integration, not behavioral instructions. Do not infer the served model
from a configured alias or silently substitute another record.
