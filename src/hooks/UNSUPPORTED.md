# Unbundled hook gaps

These hooks remain source-only because Agent Bundler v0.4.2 has no typed event
for their host lifecycle:

- `revdiff-plan-review` — Claude `ExitPlanMode` interception.
- `worktree-create` — Claude worktree creation lifecycle.
- `worktree-remove` — Claude worktree removal lifecycle.

They are excluded from every Agent Bundler package and are not emitted to
`dist/`. Their implementations and behavior tests remain until Agent Bundler
adds lossless event support. Do not reintroduce a custom compiler to ship them.
