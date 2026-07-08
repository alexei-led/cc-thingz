Inherited decisions:

- Advisory review only. No file edits.
- Goal: Pi subagents should use current/default provider aliases, e.g. `router/auto-personal`.
- `pi-subagents` behavior is authoritative:
  - explicit agent `model` wins
  - unset model inherits parent in-memory `provider/id`
  - `fallbackModels` only retries provider/model failures
  - package/custom `agentOverrides` only fill frontmatter fields that are unset

Diagnosis:

- Current cc-thingz Pi agents pin both `model` and `thinking`.
- That blocks `router/auto-personal` inheritance.
- Keeping `thinking` would still force suffixes like `router/auto-personal:low`, overriding `defaultThinkingLevel=xhigh`.
- `fallbackModels` is not a routing policy. It is failure retry.

Drift / contradiction check:

- Existing README policy says Pi agents are tuned to OpenAI Codex models. That conflicts with the new alias-driven goal.
- Runner/advisor tiering must move to router config or user/project `agentOverrides`, not package frontmatter.
- Compiler Pi allowed keys are partly stale for `pi-subagents`; notably it omits `fallbackModels` even though `pi-subagents` supports it.

Recommendation:

- Verdict: omit `model` from all four Pi agent frontmatter files.
- Also omit `thinking` from package defaults.
- Do not use `model: inherit`; it still sets the field and blocks default/override fill behavior.
- Do not add package-level `fallbackModels`.
- Keep:
  - `package: cc-thingz`
  - `tools: ...`
- Use other Pi frontmatter only with a concrete need:
  - OK if needed: `skills`, `systemPromptMode`, `inheritProjectContext`, `inheritSkills`, `defaultContext`, `maxSubagentDepth`, `completionGuard`, `toolBudget`, `memory`
  - Avoid for this package default: `model`, `thinking`, `fallbackModels`
  - Avoid unsupported/stale keys unless verified against current `pi-subagents`: `max_turns`, `prompt_mode`, `isolation`, `disallowed_tools`, `disable-model-invocation`

Risks:

- Cost/quality tiering moves to router/user config. Runner may stop being cheap unless the router handles it.
- Advisor may stop being frontier/xhigh unless default settings or overrides enforce that.
- Docs and golden generated fixtures will drift if source is changed without updating build outputs/tests.
- Users must target package runtime names in overrides, e.g. `cc-thingz.runner`.

Need from main agent:

- None. The advisory decision is clear.

Suggested execution prompt:

- No executor handoff warranted for this advisory-only task.
