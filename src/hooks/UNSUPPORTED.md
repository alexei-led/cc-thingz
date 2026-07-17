# Unbundled hook gaps

These hooks remain source-only because the current Agent Bundler event model has
no lossless host lifecycle for them:

- `revdiff-plan-review` — Claude `ExitPlanMode` interception.
- `worktree-create` — Claude worktree creation lifecycle.
- `worktree-remove` — Claude worktree removal lifecycle.

They are excluded from every package and are not emitted to `dist/`. Their
implementations and behavior tests remain until Agent Bundler supports the
required events. Do not reintroduce a custom compiler to ship them.

The portable `file-protector` and `git-guardrails` hooks are a separate gap.
They render only for Pi because the other configured targets do not yet have a
verified, lossless block/rewrite decision contract in this bundle. Do not enable
them on another target by weakening failure or deny behavior.
