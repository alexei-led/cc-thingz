---
{"description":"Remove merged local branches and stale git worktrees. Use when the user says \"cleanup branches\", \"prune worktrees\", \"tidy git\", \"remove merged branches\", \"delete merged branches\", \"gone branches\", or wants to clean local git state. NOT for creating commits, creating worktrees, or configuring git hooks.","name":"cleanup-git"}
---
<!-- Pi platform guidance -->
<!-- Use installed tool names. Discover callable tools before batching independent calls in codemode; model-only UI/orchestration tools must be called directly. -->
<!-- Read required skill/instruction files through direct read when exposed or through Code Mode. If an optional pruning extension is installed, verify its output protection semantics; do not assume nested-path protection. Code Mode composes calls; subagents or controllers own durable workflows. Async subagents notify natively: yield rather than poll. -->


# Cleanup Git

Use the target repo's own `scripts/cleanup-git.sh` if it ships one, otherwise this skill's script. Inspect a repo-provided script before relying on its safety policy. Use direct deletion only for a specifically approved exception described below; never pipe a branch list into force-delete.

```bash
scripts/cleanup-git.sh                  # preview (default)
scripts/cleanup-git.sh --apply          # execute the requested safe cleanup
scripts/cleanup-git.sh --apply --force --branch <name>  # approved ahead-commit loss
scripts/cleanup-git.sh --base <ref>     # override base detection
```

The script fetches and prunes remotes. It prefers the fetched remote default branch, then remote `main`, `master`, `trunk`, `develop`, or `dev`, then local fallbacks. `--base` overrides this choice.

## What the script decides

A branch or its worktree is a candidate when one of these holds:

- `PR merged`: GitHub confirms the PR in the target repository and base, and its merge commit is reachable from the base. This catches squash, conflict-resolved squash, and rebase merges; ahead commits count only past the PR head.
- `merged`: the branch is an ancestor of the base.
- `squash merged`: the complete branch patch is equivalent to a commit in the base. This works offline without `gh`; conflict resolution can prevent equivalence.
- `upstream gone`: only a candidate signal, not merge proof. Unique commits still keep the branch.

It skips the current worktree, current branch, base, and `main`/`master`/`trunk`/`develop`/`dev`. It keeps locked worktrees and worktrees with tracked, untracked, or ignored files, or unknown status. It keeps candidates with ahead commits or unknown ahead counts unless `--force --branch <name>` is passed for one approved target. No proof prints `skip ... (active)`; do not treat that as proof of unmerged work.

## Workflow

1. Run the preview and show the safe removals and kept objects.
2. An explicit cleanup request authorizes `--apply` for verified safe candidates. Run it without another confirmation; kept objects do not block safe removals. For a preview-only request, do not apply.
3. Report what was removed and what remains. Do not ask about every kept object unless the user wants it removed. For a risky exception, show the exact branch/path, full tip OID, unique commits, and uncommitted files (including ignored files), then ask once for permission to discard them. A reply such as “I allow it” authorizes only that described scope; execute it yourself rather than telling the user to run it.

Stop if the directory is not a git repo. If no base is found, ask for `--base <ref>`. A fetch failure makes the preview use stale refs (say so) and makes `--apply` refuse.

## Approved exceptions

After explicit user consent, recheck the tip and file list. If either changed,
ask again. For one worktree, use the using-git-worktrees cleanup script with
`--force <branch>`. For a branch-only exception, or a hook-blocked direct
cleanup, use the command-local marker:

```bash
git -c cc-thingz.cleanupApproved=<full-tip-oid> worktree remove --force <exact-path>
git -c cc-thingz.cleanupApproved=<full-tip-oid> branch -D <exact-branch>
```

Use separate commands, worktree first. The marker must match the current tip.
It does not authorize protected/current/locked worktrees, other branches,
`reset --hard`, `clean`, or force-push. Never save it with `git config`,
invent user consent, or use bulk `--force` when only one exception was approved.
The marker pins only the commit, not file contents; the agent must recheck
files immediately before executing. This is a consent attestation by the agent,
not cryptographic proof that the user approved; the hook is a mistake guard, not a security sandbox.

## Output

```text
GIT CLEANUP
Status: PREVIEW | APPLIED | BLOCKED
Base: <ref>
Remove: <branch/worktree> — <reason>
Keep: <branch/worktree> — <reason and decision needed>
Verification: <command> — pass/fail/not run
```
