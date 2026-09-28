---
{"description":"Configure safe git workflow hygiene: pre-commit/pre-push hooks, Gitleaks secret scanning, .gitignore rules, local git config, and guardrails. Use when setting up git hooks, gitleaks/git leaks, staged pre-commit checks, pre-push validation, core.hooksPath, .gitignore, or git config best practices. NOT for creating commits (use committing-code), cleaning branches/worktrees (use cleanup-git), or creating worktrees (use using-git-worktrees).","name":"configuring-git-hygiene"}
---
<!-- Pi platform guidance -->
<!-- Use installed Pi tool names exactly, including extension toolsets such as Task*, Monitor*, and Loop*. -->
<!-- When available, track work with Task* (`todo` is the fallback), run long or background commands with MonitorCreate, and schedule follow-up with LoopCreate instead of sleep/poll loops. -->


# Configure Git Hygiene

Set up project-local hygiene that stays fast enough to keep enabled. Stop if the directory is not a git repo.

## Ask first

Propose the plan (current facts, files and config to change, verification, risks) and get approval before you:

- write, replace, or merge into a hook file;
- set a `git config` value (local or global) or run `chmod`;
- run `git rm --cached`;
- install a tool, or choose whether a hook fails or skips when a tool is missing.

If the repo is dirty, show `git status --short` and ask before hook or config edits.

## Inspect

```bash
git status --short
git config --show-origin --get core.hooksPath || true
git config --show-origin --list | rg '^(file:.*\s+)?(user\.|commit\.|tag\.|pull\.|fetch\.|rerere\.|core\.hooksPath|includeIf\.)' || true
git ls-files .gitignore .pre-commit-config.yaml .gitleaks.toml 2>/dev/null || true
ls -la .git/hooks .githooks scripts/git-hooks 2>/dev/null || true
```

## Policy

- Extend the existing hook framework. Without one, use `pre-commit`, then a project-local `core.hooksPath` directory (`git config --local core.hooksPath scripts/git-hooks`).
- Pre-commit runs only on staged or affected files: format, lint, touched-config validation, staged Gitleaks scan. No full tests, full builds, installs, or network calls.
- Pre-push runs the full build, test, type, and lint validation, plus a broader secret scan when practical.
- Run Gitleaks with `--redact`, and keep secret values out of chat and external tools.
- Hooks never auto-commit or restage files unless the repo already does.
- A hook that blocks legitimate work gets tuned; `--no-verify` is not the fix.
- `.gitignore` patterns come from real artifacts and stay narrow.

Details by topic:

- Hook scripts and pre-push input → [hooks.md](references/hooks.md)
- Gitleaks commands, missing tool, false positives → [gitleaks.md](references/gitleaks.md)
- `.gitignore` and untracking files → [gitignore.md](references/gitignore.md)

## Verify

- Hooks path: `git config --local --get core.hooksPath`, then run the hook directly on safe fixture input.
- Gitleaks: a staged or repo scan with `--redact`, when installed.
- `.gitignore`: `git check-ignore -v <path>` and `git ls-files <path>`.
- Hook scripts: the project's shell lint, format, and test gates.

Done when the relevant build/test/lint checks pass on what you changed, or you name each check that did not run and why.

## Output

```text
GIT HYGIENE CONFIG
Scope: hooks | gitleaks | gitignore | config | guardrails
Status: PROPOSED | APPLIED | BLOCKED
Current state: <facts from git config/files>
Plan: <change and why>
Changes: <file/config edited>
Verification: <command> — pass/fail/not run
Next: <install tool, run hook, or push validation>
```
