# Tune Git and file protections

The default hooks allow ordinary development commands. Git still blocks
destructive operations such as a hard reset or a forced clean. An explicit
clean preview and an index-only unstage are allowed. The file protector blocks
writes to sensitive locations and key or secret files; a source filename such
as `password-validator.ts` is not itself a secret. Environment files such as
`.env.local` and common lockfiles warn instead of blocking. The release guard
remains opt-in; read-only release queries can be piped or chained.

These hooks prevent common mistakes. They do not sandbox scripts or intercept
every possible way to run a command or edit a file.

## User settings and project profiles

Edit `~/.claude/hook-config.json`, or set `CLAUDE_HOOK_CONFIG` to an absolute
path outside the project in the environment that starts the agent. Both hooks
read this file, including on Pi. Git hook settings require `jq`. The top-level `gitGuardrails` and
`fileProtector` objects contain user defaults; `projects` groups both hooks
under one user-owned checkout profile.
Use the canonical absolute checkout path (for example, from `pwd -P` at the
checkout root) for each project profile:

```json
{
  "gitGuardrails": {
    "cleanupPolicy": "strict"
  },
  "projects": {
    "/home/dev/work/sandbox": {
      "gitGuardrails": {
        "blockPatterns": ["^git push .*production"]
      },
      "fileProtector": {
        "allowPaths": ["tests/fixtures/demo.pem"],
        "protectedPatterns": ["^settings/local-auth[.]ini$"]
      }
    }
  }
}
```

- **Git:** The effective Git worktree, including a literal `git -C` destination,
  selects the profile. Each linked worktree can have its own profile.
  `allowForcePush` and `cleanupPolicy` override the corresponding global
  options for that worktree. Opt into either relaxation only where you
  accept lost work or overwritten history. Project block patterns add to
  global block patterns; neither option disables an explicit block pattern.
  The legacy global `git-guardrails` keys still work. See
  [Git cleanup policy](git-cleanup.md) for the cleanup modes.
- **Files:** The nearest configured ancestor of the tool's working directory
  selects the profile. `allowPaths` uses exact, project-relative paths and
  exempts only built-in blocks. It does not exempt symlink aliases, files
  outside the profile, or explicit user or project protections.
  Project `protectedPatterns` are regular expressions against project-relative
  paths; global `protectedPatterns`, `warnPatterns`, and `lockFilePatterns`
  replace their respective defaults and match requested and resolved paths.
- **Legacy exclusions:** With no project profile, legacy
  `.claude/file-protector.json` regex exclusions still apply to built-in blocks
  on absolute paths, not to explicit user rules or symlink aliases. Prefer exact
  user-owned `allowPaths` for new exceptions. Set
  `fileProtector.allowLegacyProjectExcludes` to `false` to stop reading
  repository-controlled exclusions.
- **Pi:** [Bash permission rules](pi-extensions.md#bash-permission-rules) are
  separate. A Pi allow does not override either hook. Use `/permissions` to
  inspect Pi's Bash rules.

If a hook blocks legitimate work, use the reported rule and the smallest
project setting that addresses it. Avoid changing global protections for a
one-project exception.
