# Agent Bundler migration status

`agentbundle.json` is the only build pipeline. Do not add a second compiler or a
post-build output rewriter.

## Working with the current Agent Bundler tree

- `agbun check` detects generated drift without rewriting `dist/`.
- Flat agents accept per-agent target sidecars under
  `src/agents/<name>.md.agentbundler/targets/`.
- Claude and Pi agent envelopes are preserved; supported agents also render for
  Copilot, Cursor, and Grok.
- Pi hooks receive a declared safe environment instead of inheriting secrets.
- The Pi archive bundles and activates `pi-subagents` when package agents exist.
- Pi-native extension trees under `src/plugins/pi/<asset>/` copy declaratively;
  only explicit `piExtensions` entries register in the aggregate manifest.
- `agbun package --out DIR` creates deterministic target-root archives for all
  six supported targets.
- Release CI is configured to attach those archives to GitHub releases.

These capabilities require a compatible installed Agent Bundler. CI installs
the current release during each run.

## Source-only compatibility assets

These assets remain tested source but are not emitted to `dist/`:

- `src/hooks/revdiff-plan-review/` — needs Claude `ExitPlanMode`.
- `src/hooks/worktree-create/` — needs Claude worktree-create lifecycle.
- `src/hooks/worktree-remove/` — needs Claude worktree-remove lifecycle.
- `src/pi-extensions/` — the legacy `hook-runner`, `permission-gate`,
  `plan-mode`, and shared bridge lack a complete bundled hook configuration.

The generated Pi package contains Agent Bundler's typed hook adapter, bundled
`pi-subagents`, and native ask-user-question, structured-output, and todo
extensions. It does not contain the legacy hook-runner stack.

## Remaining Agent Bundler gaps

1. Lossless Claude lifecycle events for exit-plan mode and worktree creation and
   removal.
2. A complete declarative migration for the legacy Pi hook-runner stack and
   its configuration.
3. Portable block/rewrite decisions for file protection and git guards outside
   Pi, with target-native failure semantics.
4. Lossless Cursor edit matching and Pi notification mapping.
5. Codex model and reasoning-effort frontmatter mapping. Codex profiles now
   render at target-root `.codex/agents/*.toml`, outside plugin contents.
6. Non-mutating native validators for Codex, Pi, Copilot, and Cursor. Release
   tests can inspect/install archives, but some vendor runtime behavior still
   needs vendor-backed smoke environments.
7. Vendor-backed runtime smoke environments for each published target package.

Unsupported behavior must stay explicit. Do not emulate it with target-specific
files written after `agbun build`.
