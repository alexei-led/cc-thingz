---
{"allowed-tools":["Read","Edit","Write","Grep","Glob","AskUserQuestion","Bash(git rev-parse *)","Bash(git status *)","Bash(git config *)","Bash(git ls-files *)","Bash(git check-ignore *)","Bash(git diff *)","Bash(git rm --cached *)","Bash(chmod *)","Bash(mkdir *)","Bash(ls *)","Bash(rg *)","Bash(gitleaks *)","Bash(pre-commit *)","Bash(make *)"],"context":"fork","description":"Configure safe git workflow hygiene: pre-commit/pre-push hooks, Gitleaks secret scanning, .gitignore rules, local git config, and guardrails. Use when setting up git hooks, gitleaks/git leaks, staged pre-commit checks, pre-push validation, core.hooksPath, .gitignore, or git config best practices. NOT for creating commits (use committing-code), cleaning branches/worktrees (use cleanup-git), or creating worktrees (use using-git-worktrees).","name":"configuring-git-hygiene","user-invocable":true}
---

# Configure Git Hygiene

Set up project-local git hygiene. Keep hooks fast enough to stay enabled. Do not overwrite hooks, change global config, remove tracked files, or install tools without user approval.

## Scope

Use this skill for:

- Git hook setup or migration to a project hooks directory.
- Staged-file pre-commit checks.
- Full pre-push validation.
- Gitleaks secret scanning.
- `.gitignore` rules and tracked-file cleanup.
- Local git config such as `core.hooksPath`, `includeIf`, signing, pull behavior, and pruning.

Do not use this skill for:

- Commit grouping or commit messages — use `committing-code`.
- Worktree creation — use `using-git-worktrees`.
- Branch/worktree cleanup — use `cleanup-git`.

## Step 1: Inspect Current State

Run read-only checks first:

```bash
git rev-parse --show-toplevel
git status --short
git config --show-origin --get core.hooksPath || true
git config --show-origin --list | rg '^(file:.*\s+)?(user\.|commit\.|tag\.|pull\.|fetch\.|rerere\.|core\.hooksPath|includeIf\.)' || true
git ls-files .gitignore .pre-commit-config.yaml .gitleaks.toml 2>/dev/null || true
ls -la .git/hooks .githooks scripts/git-hooks 2>/dev/null || true
```

If a hook framework already exists, extend it. Do not replace it.

## Step 2: Load Focused References

- Hook files or `core.hooksPath` changes: read [hooks.md](references/hooks.md).
- Gitleaks setup or secret scanning: read [gitleaks.md](references/gitleaks.md).
- `.gitignore` or `git rm --cached`: read [gitignore.md](references/gitignore.md).

## Step 3: Propose Before Editing

State current facts, proposed files/config, verification, and risks. Ask before:

- writing or replacing hook files
- running `git config --local` or any global config command
- running `chmod`
- running `git rm --cached`
- choosing skip-vs-fail behavior for missing tools

## Step 4: Apply Safely

Rules:

- Prefer existing project convention, then `pre-commit`, then project-local `core.hooksPath`.
- Use project-local config for shared repos: `git config --local core.hooksPath scripts/git-hooks`.
- Keep pre-commit staged/affected-file only; do not run full tests, full builds, installs, or network calls there.
- Put full build/test/type/lint validation in pre-push.
- Redact secret-scan output. Never paste secret values into external tools.
- Use narrow `.gitignore` patterns derived from actual artifacts.
- Do not auto-commit from hooks unless the project already has that convention.

## Step 5: Verify

Run the narrowest proof for the changed component:

- Hook path/config: `git config --local --get core.hooksPath` and direct hook execution with safe fixture input when possible.
- Gitleaks: staged or repo scan command with `--redact` when the tool is available.
- `.gitignore`: `git check-ignore -v <path>` and `git ls-files <path>` for affected files.
- Hook scripts: project shell lint/format/test gate when available.

## Output

```text
GIT HYGIENE CONFIG
==================
Scope: hooks | gitleaks | gitignore | config | guardrails
Status: PROPOSED | APPLIED | BLOCKED

Current state:
- <facts from git config/files>

Plan:
- <change and why>

Changes:
- <file/config edited>

Verification:
- <command> — pass/fail/not run

Next:
- <install tool, run hook, or push validation>
```

## Failure Handling

- Not a git repo: say so and stop.
- Existing hook would be overwritten: stop and merge manually.
- Tool missing: ask whether the hook should fail closed or skip with a clear message.
- Dirty repo before hook/config edits: show `git status --short` and ask before proceeding.
- Hook blocks legitimate work: diagnose and tune the hook; do not recommend `--no-verify` as the fix.