# Git Hook Scripts

## Existing hooks

Read any hook at the target path and merge its behavior into the new one. Plain `.git/hooks/*` files suit local experiments only; shared setups belong in `pre-commit` or a committed hooks directory.

## Pre-commit

Discover staged files NUL-safely:

```bash
git diff --cached --name-only -z
```

A generated-artifact drift check belongs here when source files changed.

## Pre-push

Read stdin as ref updates, and skip validation only for deletion-only pushes:

```bash
while read -r local_ref local_sha remote_ref remote_sha; do
  [ "$local_sha" = 0000000000000000000000000000000000000000 ] && continue
  # validate pushed update
  : "$local_ref" "$remote_ref" "$remote_sha"
done
```

## Tool selection

- Use the tools the project config or package dependencies declare.
- Otherwise use the fastest compatible tool with an established fallback, for example Oxfmt → Biome → Prettier and Oxlint → Biome → ESLint. Keep the order in the hook, not in one environment variable per tool, and report the selected tool.
- Run one formatter and one linter per file type, not overlapping passes.

## Script discipline

- Bash hooks start with `#!/usr/bin/env bash` and `set -euo pipefail`.
- Quote paths and pass `--` before user-controlled operands.
- Send diagnostics to stderr when another tool consumes stdout.
- Exit non-zero to block and zero to allow.
- Commit hook scripts as executable.
