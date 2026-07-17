# Portable hook boundaries

These source hooks are not emitted because the current target adapters lack a
lossless portable lifecycle event:

- `worktree-create` — Claude worktree creation lifecycle.
- `worktree-remove` — Claude worktree removal lifecycle.

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
