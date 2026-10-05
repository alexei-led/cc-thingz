---
{"description":"Create normal git commits with logical grouping. Use when committing, saving changes, creating commits, or grouping work into commits. For drafting or editing commit messages without committing, use writing-style. NOT for amending, rebasing, force-pushing, or rewriting history.","name":"committing-code"}
---

# Commit Changes

Group the working-tree changes by purpose and commit them as normal commits. Done
when each intended change is in one logical commit and the final `git status` is
shown.

## Gather state

Run `scripts/commit-state.sh gather`. It is read-only and prints repo state,
changed paths, diff stats, suspicious paths, and recent commits. Without it, run
`git status`, `git diff --stat`, and `git log --oneline -8`. Read the full diff
(`scripts/commit-state.sh full-diff`) when the stats do not make the grouping
obvious. Treat the helper output as a hint, not proof.

Stop and report the state verbatim when there is nothing to commit, the directory
is not a git repository, HEAD is detached, or a rebase or merge is in progress.

## Group

- One purpose, a few files, and no suspicious paths: one commit. Do not invent a
  split.
- Mixed changes: group by purpose (feature, fix, refactor, docs, CI or config)
  from diff evidence, not filenames. Keep a change and its tests together.
- Use writing-style for message wording. Keep the repo's syntax and required
  trailers; lead with the concrete change and add a body only for non-obvious
  reasons, consequences, or migration steps.
- Match the message style of recent commits. Read
  [conventions.md](references/conventions.md) when there is no history to match or
  the user asks for a specific format.

## Propose and commit

Show the plan and the evidence it rests on:

```text
Based on: git status, diff stat, last 8 commits (style: conventional)

1. fix(validation): reject empty email
   - src/validation.ts
   - tests/validation.test.ts
2. docs: document the --dry-run flag
   - README.md
```

An explicit commit request authorizes staging and committing this plan. Proceed
without a second approval, and do not ask again for each group. Ask first only
when the user rejects the grouping, or when the scope, sensitive content, or a
history-changing action differs from what was requested.

Hard rules:

- Never stage likely secrets: `.env` files, private keys, certificates, credential
  or token files, or files whose content looks like a secret. Flag each one to
  the user. This check does not replace a secret scanner.
- If a pre-commit hook rejects a commit, report its error verbatim. Do not retry
  with `--no-verify` and do not amend.

## Report

Show the created commits, the final `git status`, and any files left uncommitted.
