---
{"description":"Remove merged local branches and stale git worktrees. Use when the user says \"cleanup branches\", \"prune worktrees\", \"tidy git\", \"remove merged branches\", \"delete merged branches\", \"gone branches\", or wants to clean local git state. NOT for creating commits, creating worktrees, or configuring git hooks.","name":"cleanup-git"}
---
<!-- Pi platform guidance -->
<!-- Use installed tool names. Discover callable tools before batching independent calls in codemode; model-only UI/orchestration tools must be called directly. -->
<!-- Prefer direct read for required skill/instruction files when exposed; otherwise use Code Mode only after verifying output protection, not assumed nested-path protection. Code Mode composes calls, not durable workflows or context-mode data processing. Async subagents notify natively: yield rather than poll. -->


# Cleanup Git

All deletion goes through the cleanup script: the target repo's own `scripts/cleanup-git.sh` if it ships one, otherwise this skill's `scripts/cleanup-git.sh`. Do not hand-write branch or worktree deletion commands.

```bash
scripts/cleanup-git.sh                  # preview (default)
scripts/cleanup-git.sh --apply          # delete after user approval
scripts/cleanup-git.sh --apply --force  # also delete branches with ahead commits
scripts/cleanup-git.sh --base <ref>     # override base detection
```

The script fetches and prunes remotes, then picks the base from the remote default branch, then local or remote `main`, `master`, `trunk`, `develop`, or `dev`.

## What the script decides

A branch or its worktree is a candidate when one of these holds:

- `PR merged`: `gh pr view <branch>` reports `MERGED`. This catches squash and rebase merges; ahead commits count only past the PR head commit.
- `upstream gone`: the tracking branch was deleted.
- `merged`: the branch is an ancestor of the base.

It always skips the current worktree, the current branch, the base, and `main`/`master`/`trunk`/`develop`/`dev`. It keeps dirty worktrees. It keeps candidates with ahead commits, or an unknown ahead count, unless `--force` is passed. A branch with none of these signals prints `skip ... (active)`; without `gh`, squash-merged branches land there.

## Workflow

1. Run the preview and show it. Read each line literally: `remove <worktree>` and `delete <branch>` are candidates; `KEEP ... (dirty)`, `KEEP ... (N ahead — use --force)`, and `KEEP ... (ahead unknown — run git fetch ...)` need the user; `skip` lines for the current, base, or protected branch are guarded; mention `skip ... (active)` lines when `gh` is unavailable.
2. Present every `KEEP` line as a decision for the user.
3. Ask before `--apply`. Add `--force` only when the user confirms the ahead commits are throwaway.

Stop if the directory is not a git repo. If no base is found, ask for `--base <ref>`. A fetch failure makes the preview use stale refs (say so) and makes `--apply` refuse.

## Output

```text
GIT CLEANUP
Status: PREVIEW | APPLIED | BLOCKED
Base: <ref>
Remove: <branch/worktree> — <reason>
Keep: <branch/worktree> — <reason and decision needed>
Verification: <command> — pass/fail/not run
```
