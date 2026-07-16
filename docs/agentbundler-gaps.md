# Agent Bundler v0.4.2 gaps

`agentbundle.json` is the only build pipeline. Agent Bundler renders skills,
agents, typed hook payloads, package manifests, target hook manifests, and the
Pi aggregate hook runtime.

## Source-only compatibility assets

The following assets are intentionally not in any Bundle package:

- `src/hooks/revdiff-plan-review/` — needs Claude `ExitPlanMode`.
- `src/hooks/worktree-create/` — needs Claude worktree-create lifecycle.
- `src/hooks/worktree-remove/` — needs Claude worktree-remove lifecycle.
- `src/pi-extensions/` — needs Pi native-resource copy and extension
  registration.

They are retained with tests but are not emitted to `dist/`. See
`src/hooks/UNSUPPORTED.md` for the hook boundary.

## Requested Agent Bundler capabilities

1. Lossless Claude lifecycle events for exit-plan-mode and worktree creation and
   removal.
2. Pi native-resource packaging with `package.json.pi.extensions` registration.
3. Portable block/rewrite hook decisions for non-Pi targets, or an explicitly
   equivalent native command-exit contract.
4. Cursor edit matcher mapping.
5. Pi notification event mapping.
6. Vendor installation, publishing, and runtime smoke-test contracts.

Do not add a cc-thingz compiler or post-processing adapter for these gaps.
