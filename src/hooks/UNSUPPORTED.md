# Portable hook boundaries

Every source hook renders to at least one target; package JSON `targets` lists
decide where. `smart-lint` is excluded from Cursor, which lacks a lossless edit
matcher. The notify and smart-lint target matrix is in
`docs/agentbundler-gaps.md`.

Pi supports user-configured plan review through the compatibility runner's
synthetic `ExitPlanMode` event. No personal review integration is bundled.

## Guard coverage

`file-protector` and `git-guardrails` are portable where an adapter can preserve
the matcher and deny decision:

- Claude, Codex, Copilot, Grok, and Pi receive both guards.
- Cursor receives command-only `git-guardrails`.

Some non-Pi target adapters treat crash or timeout behavior as advisory even
when a normal deny response blocks the tool call. Each such target has an
explicit source acknowledgment. Do not broaden target lists or remove those
acknowledgments without a target-runtime deny/crash smoke test.
