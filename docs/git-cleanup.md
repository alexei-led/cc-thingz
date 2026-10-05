# Git cleanup and guardrails

A request to clean merged branches/worktrees authorizes the agent to preview and
apply verified safe removals. It does not need a second confirmation. Preview-only
requests stay read-only. Kept objects do not block safe cleanup.

## Merge proof

The bulk and single-worktree scripts fetch first. Remote-tracking integration
refs take precedence over stale local branches. A merge is proven by:

- Git ancestry;
- a merged GitHub PR for the target repository and base, a reachable merge
  commit, and no local commits outside the merged PR head;
- an equivalent complete squash patch in the integration history, without gh.

Conflict-resolved squash and rebase merges may need PR metadata because their
patches differ. A deleted upstream alone is not merge proof. Fetch failure
blocks script execution; the pre-tool hook uses existing refs and tells the
agent to fetch first.

The hook allows verified branch force-deletion after squash, plus ordinary
worktree removal followed by branch deletion in the same command. Missing or
invalid proof stays blocked. User block patterns remain authoritative.

## Files and protected objects

Automatic cleanup preserves tracked changes, untracked files, and ignored
files. Ignored files can contain local credentials or other valuable data;
never treat them as disposable just because Git ignores them. Locked, current,
main, and integration worktrees and protected branches remain guarded.
Bulk `--force` requires `--branch <name>` and does not remove dirty or locked
worktrees. An unscoped force sweep is rejected.

## Explicit consent, without manual commands

For an exception, the agent shows the exact repository, branch/path, full tip
OID, unique commits, and all uncommitted files. It asks once to discard that
specific work. “I allow it” authorizes that described operation, not every
destructive Git command. The agent rechecks the tip and files, then executes
it itself. If state changed, consent must be renewed.

The one-worktree script accepts `--force <branch>` for such consent. Direct
cleanup can attest consent with a command-local Git configuration option:

```sh
git -c cc-thingz.cleanupApproved=<full-tip-oid> worktree remove --force <exact-path>
git -c cc-thingz.cleanupApproved=<full-tip-oid> branch -D <exact-branch>
```

Run these separately, worktree first. The hook compares the approved OID to the
target's current tip. It ignores persisted approval config and rejects protected
targets and lock overrides even with consent. The marker never permits reset,
clean, or force-push; custom block patterns can still deny the call.

This is an agent's consent attestation, not an authenticated user grant.
The portable command hook cannot read or authenticate a conversational answer.
The marker pins the commit, not the worktree file contents: rechecking files is
the agent's responsibility, not a hook-enforced content snapshot.
An agent must never invent consent, persist the marker, or reuse it for another
target. Like the existing shell-command analyzer, this is a mistake guard, not
a sandbox: scripts, Git aliases, environment manipulation, and concurrent
repository changes are not a security boundary.

## Sources and checks

- Hook: `src/hooks/git-guardrails/{hook.sh,decide.py}`.
- Bulk: `src/skills/cleanup-git/scripts/cleanup-git.sh`.
- One worktree: `src/skills/using-git-worktrees/scripts/cleanup-worktree.sh`.
- Policy: the corresponding skills; regression tests in
  `tests/hooks/test_git_cleanup_policy.py` and
  `tests/test_cleanup_git_policy.py`.

Generated adapters ship from these sources to all six targets. Run
`make build`, `make fmt`, and `make ci` before release.
