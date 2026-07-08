# GitHub CLI Integration

Read when `gh` is available in the environment and PR-state detection is needed.

## When gh changes the result

`gh pr list --state merged` is the source of truth for squash and rebase merges.
`git merge-base --is-ancestor` fails for those — the branch tip was never
merged into the base; the commits were rewritten. Without `gh`, a
squash-merged branch looks ahead and is kept; with `gh`, the merged PR
confirms it is safe to remove.

Availability check:

```bash
if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
  USE_GH=1
fi
```

## PR state lookup

```bash
gh pr list --head "$branch" --state merged --json number,mergedAt \
  --jq 'length > 0'
```

Returns `true` when a merged PR exists for the branch. Use `--repo owner/repo`
when the remote is not the default.

Fallback when the branch has been deleted from the remote:

```bash
gh pr list --head "$branch" --state all --json state \
  --jq '.[0].state // "NONE"'
```

A result of `"MERGED"` means the branch is removable even if `gh pr list
--state merged` returns empty (the branch ref is already gone from the remote).

## Ahead-commit adjustment for squash/rebase merges

For a squash-merged branch, the local branch tip will appear ahead of base
because none of its commits are literally in the base history. Do not count
commits added _before_ the PR head as "ahead". Only commits pushed after the
merge date matter:

```bash
pr_merged_at=$(gh pr view "$pr_number" --json mergedAt --jq '.mergedAt')
ahead=$(git log --oneline --after="$pr_merged_at" "$base..$branch" | wc -l)
```

If `$ahead` is zero, the branch is safe to remove without `--force`.

## Rate limits and offline behaviour

`gh` calls count against the GitHub REST API rate limit (5 000/hr for
authenticated users). For repos with many branches, batch lookup with:

```bash
gh pr list --state merged --limit 200 --json headRefName \
  --jq '[.[].headRefName]'
```

Cache the result once per cleanup run; do not call `gh` per branch.

When `gh auth status` fails (offline, token expired, or no remote), fall back
to git-only checks and note that squash/rebase-merged branches may be retained.
