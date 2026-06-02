---
description: Remove merged local branches and stale git worktrees. Use when the user
  says "cleanup branches", "prune worktrees", "tidy git", "remove merged branches",
  "delete merged branches", "gone branches", or wants to clean local git state. NOT
  for creating commits, creating worktrees, or configuring git hooks.
name: cleanup-git
---

<!-- Pi platform guidance -->
<!-- Use Pi tool names exactly: read, bash, edit, write, ask_user_question, structured_output, todo, Agent, get_subagent_result, steer_subagent, web_search, web_answer, web_research. -->
<!-- Use Agent, get_subagent_result, and steer_subagent for delegated work. -->
<!-- Use ctx7 or npx ctx7@latest through bash when Context7 documentation lookup is required. -->

# Cleanup Git

Clean local git branches and worktrees after work has merged. Dry-run first. Destructive commands require user approval.

Prefer a repo-local `scripts/cleanup-git.sh` when the target repo ships one. If it does not, use the bundled skill script from this skill's `scripts/` directory. Do not improvise destructive cleanup commands outside the script workflow.

## Command

Run from anywhere inside a repository:

```bash
scripts/cleanup-git.sh
scripts/cleanup-git.sh --apply
scripts/cleanup-git.sh --apply --force
scripts/cleanup-git.sh --base <ref>
```

## Branch Detection

The script fetches/prunes remotes, then chooses the comparison branch:

1. Remote default branch from `refs/remotes/<remote>/HEAD`.
2. Local `main`, `master`, `trunk`, `develop`, or `dev`.
3. Remote `<remote>/{main,master,trunk,develop,dev}`.

Use `--base <ref>` only for unusual repositories.

## What It Removes

- Worktrees whose branch has a GitHub PR in `MERGED` state, is merged into the detected base branch, or whose upstream is gone.
- Local branches with the same criteria.

When `gh` is available, PR `MERGED` state is the source of truth for squash/rebase merges. Do not miss those just because `git merge-base --is-ancestor` fails after history rewrite. If no PR is found, or `gh` is unavailable, fall back to the git-based checks.

## Guards

Hard guards:

- Skip the current worktree.
- Skip the current branch.
- Skip the detected base branch and common long-lived branches: `main`, `master`, `trunk`, `develop`, `dev`.
- Keep worktrees with uncommitted changes.

Soft guard:

- Keep items with commits ahead of the base branch. `--force` overrides only this guard.
- For merged PRs, treat only commits added after the PR head as "ahead". A squash/rebase-merged branch with no new local commits is still removable.

## Workflow

1. Run `scripts/cleanup-git.sh` and show the preview.
2. Read reasons literally: `remove ... (PR merged)`, `remove ... (upstream gone)`, `KEEP ... (dirty)`, `KEEP ... (PR merged, N ahead — use --force)`.
3. Surface every `KEEP` line as a human decision.
4. Ask before running `scripts/cleanup-git.sh --apply`.
5. Use `--force` only when the user confirms ahead commits are throwaway.

## Output

```text
GIT CLEANUP
===========
Status: PREVIEW | APPLIED | BLOCKED
Base: <ref>

Remove:
- <branch/worktree> — <reason>

Keep:
- <branch/worktree> — <reason and user decision needed>

Verification:
- <command> — pass/fail/not run
```

## Failure Handling

- Not a git repo: say so and stop.
- Base branch not found: ask for `--base <ref>`.
- Fetch fails during preview: report that refs may be stale.
- Fetch fails during apply: stop; do not delete with stale refs.
- Dirty worktree: keep it and ask the user what to do.
- Ahead commits: keep unless the user explicitly approves `--force`.
