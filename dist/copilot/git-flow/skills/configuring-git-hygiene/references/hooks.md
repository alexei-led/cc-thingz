# Git Hook Rules

## Strategy

Prefer, in order:

1. Existing project hook framework.
2. `pre-commit` when the repo already uses it or the team wants a multi-language framework.
3. Project-local hooks directory with `core.hooksPath`.
4. Manual `.git/hooks/*` only for local experiments.

Preserve existing hooks. If a target hook already exists, read it and merge behavior instead of replacing it.

## Pre-Commit

Pre-commit should be fast and local to staged or affected files.

Use it for:

- format/lint staged files
- validate touched manifests or config
- staged Gitleaks scan
- generated-artifact drift checks when source files changed

Do not use it for:

- full test suites
- full builds
- network calls
- package installs

When writing shell hooks, prefer NUL-safe staged-file discovery:

```bash
git diff --cached --name-only -z
```

## Pre-Push

Pre-push catches CI-style failures before code leaves the machine:

- full build or generated-artifact check
- full test suite
- type checks and lint too slow for pre-commit
- broader secret scan when practical

Read pre-push stdin as ref updates. Skip validation only for deletion-only pushes.

```bash
while read -r local_ref local_sha remote_ref remote_sha; do
  [ "$local_sha" = 0000000000000000000000000000000000000000 ] && continue
  # validate pushed update
  : "$local_ref" "$remote_ref" "$remote_sha"
done
```

## Script Discipline

- Use `#!/usr/bin/env bash` with `set -euo pipefail` for Bash hooks.
- Quote paths and pass `--` before user-controlled operands when supported.
- Send diagnostics to stderr when stdout is consumed by another tool.
- Exit non-zero to block; exit zero to allow.
- Make committed hook scripts executable.
- Do not auto-commit or mutate staged files unless the repo already does that explicitly.
