# Agent Bundler port status

`agentbundle.json` is the only cc-thingz package pipeline. `agbun build` renders
`dist/`; `agbun check` detects drift; `agbun package` creates the six target-root
release archives. Do not add a custom compiler or post-build copier.

## CC-Thingz port coverage

The current source restores behavior that belongs to this package rather than to
a portable hook schema:

- Codex receives `smart-lint` through its native `PostToolUse` matcher.
- Grok receives the synchronous `notify-grok` hook. Pi notifications are handled
  by the native compatibility runner.
- Pi receives `ccgram hook` at session start, stop, and session end.
- Pi native assets register ask-user-question, hook-runner, permission-gate,
  plan-mode, structured-output, and todo.
- The Pi compatibility runner loads only Pi-specific defaults from
  `extensions/hooks.json`: ExitPlanMode/revdiff review and notifications. It
  does not repeat portable Agent Bundler hooks.
- File protection and git guardrails render wherever the current target adapter
  can express their matcher and deny protocol. Source acknowledgments record
  targets where crash/timeout fail-closed behavior is advisory.

## Agent Bundler blockers

These are generator or vendor-contract gaps, not reasons to restore custom
build scripts:

1. Claude `WorktreeCreate` and `WorktreeRemove` lifecycle events.
2. Codex agent `model` and `model_reasoning_effort` fields. cc-thingz sidecars
   retain the intended values, but current generated profiles support only the
   documented name, description, sandbox, and instructions fields.
3. Cursor lossless `edit` matcher translation. File protection remains excluded
   there; command-only git guards are supported.
4. Portable Pi `Notification` mapping. Pi uses its native compatibility runner.
5. Full vendor CLI runtime smoke coverage. Archive/install tests run where a
   vendor CLI is available; Cursor needs `CURSOR_API_KEY` and vendor state.

## Intentional target differences

- Codex agents are target-root `.codex/agents/*.toml` profiles, not plugin
  assets. The Codex plugin contract does not define plugin-contained agents.
- Gemini is retired.
- Pi has native extensions and its own permission/plan compatibility layer;
  those are not forced into portable hook descriptors.
- `file-protector` is absent from Cursor because an edit matcher would lose
  semantics. `git-guardrails` uses Cursor's command matcher.

## Runtime validation status

Checked in the repository:

- generated hook matrices, target manifests, archives, and source/output drift;
- Pi guard deny protocol and safe hook environment;
- native Pi extension registration and all copied compatibility dependencies;
- permission-gate safe, headless-deny, user-deny, validated-update, and timeout
  behavior;
- plan-mode ExitPlanMode bridge, updated-plan, deny, and timeout behavior;
- hook-runner compatibility config and no duplicate portable default hooks.

Vendor install/load smoke tests run sequentially when the corresponding CLI is
installed. Cursor smoke is skipped without `CURSOR_API_KEY`.
