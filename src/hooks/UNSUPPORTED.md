# Portable hook boundaries

Every source hook renders to at least one target; package JSON `targets` lists
decide where. `smart-lint` is excluded from Cursor, which lacks a lossless edit
matcher. The notify and smart-lint target matrix is in
`docs/agentbundler-gaps.md`.

`revdiff-plan-review` is not a Claude-only loss. Pi ships it as a native
compatibility-runner command for plan-mode's synthetic `ExitPlanMode` review.

## Guard coverage

`file-protector` and `git-guardrails` are portable where an adapter can preserve
the matcher and deny decision:

- Claude, Codex, Copilot, Grok, and Pi receive both guards.
- Cursor receives command-only `git-guardrails`.

Some non-Pi target adapters treat crash or timeout behavior as advisory even
when a normal deny response blocks the tool call. Each such target has an
explicit source acknowledgment. Do not broaden target lists or remove those
acknowledgments without a target-runtime deny/crash smoke test.
