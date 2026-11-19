# cc-thingz Hook Policy

Use this reference for packaged Git guardrails and file protection, not Git
pre-commit hooks. Keep user configuration private and read-only until the user
approves the exact change and its risk.

## Locate and inspect

1. Identify the target, the observed blocked command or file, its hook decision,
   and the checkout root. Check whether the target actually ships each hook.
   For Git, use `git rev-parse --show-toplevel`; resolve the physical path.
   Linked worktrees have distinct roots.
2. The user policy is `CLAUDE_HOOK_CONFIG` when set, otherwise
   `~/.claude/hook-config.json`. Inspect only relevant keys; never print
   secrets. Git reads this policy only when `jq` is available.
3. Global keys `gitGuardrails` and `fileProtector` apply to the user.
   The user-owned `projects` map groups both hooks under a canonical absolute
   checkout path. File protection selects the nearest configured ancestor of
   its tool cwd; Git selects the actual Git worktree, including literal
   `git -C`. Repository-controlled settings are not the same as this profile.
4. Pi's `permissionGate` in user or trusted project settings is a separate
   Bash warning gate; `/permissions` shows those rules. A Pi allow does not
   override a hook deny. Neither layer is a sandbox.

## Tune

- Propose the smallest user-owned global or project change with its exact
  JSON path, behavior, security risk, and verification. Ask before changing
  the policy; never weaken a user deny or install, remove, or disable hooks
  without consent.
- Under `projects.<absolute-root>.gitGuardrails`, `blockPatterns` adds
  regex denies to global denies. `allowForcePush` and `cleanupPolicy`
  override those global settings only for that worktree. `relaxed` cleanup
  may discard uncommitted and ignored files; say so before proposing it.
- Under `projects.<absolute-root>.fileProtector`, `allowPaths` is a list
  of exact project-relative paths exempted from built-in blocks. It does not
  exempt symlink aliases, outside paths, or explicit user or project denies.
  `protectedPatterns` adds regex denies against project-relative paths.
- Global `fileProtector.protectedPatterns`, `warnPatterns`, and
  `lockFilePatterns` replace the corresponding default list; `[]` clears
  it. Avoid replacing a global list for a one-project exception. The legacy
  `.claude/file-protector.json` exclusions may relax built-in blocks when no
  user profile applies; set `allowLegacyProjectExcludes: false` to disable
  them after checking migration impact.
- Preserve unrelated keys. After approval, validate JSON and run a harmless
  synthetic hook payload in a temporary directory with the intended policy;
  check one allowed case, one blocked case, and project boundaries. Do not
  execute the destructive command or print its secrets. Report which target
  adapters and hook failure semantics were verified.
