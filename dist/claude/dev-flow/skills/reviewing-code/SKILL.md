---
{"allowed-tools":["Task","TaskOutput","TaskCreate","TaskUpdate","TaskList","AskUserQuestion","Read","Grep","Glob","LS","Bash(git *)","Bash(gh pr *)","Bash(gh api *)"],"argument-hint":"[deep] [team] [external]","context":"fork","description":"Use when reviewing changed code, PRs, diffs, or specific files. Finds evidence-backed defects in security, correctness, tests, reliability, performance, maintainability, and docs. Supports quick, standard, deep, team, and external-review modes. NOT for repo-wide architecture review, general codebase exploration, fixing issues (use fixing-code), improving tests without a code review (use improving-tests), or applying refactors (use refactoring-code).","name":"reviewing-code","user-invocable":true}
---
# Code Review

## Platform workflow additions

Track phases with `TaskCreate` and `TaskUpdate` when available:

1. Scope resolved.
2. References loaded.
3. Evidence gathered.
4. Findings consolidated.
5. Report emitted.

## Arguments

If `$ARGUMENTS` is passed, interpret these keywords:

- `quick`: changed lines plus direct context; security and correctness only.
- `deep`: all dimensions from the host skill.
- `team`: parallel reviewer sub-tasks, then one consolidated report.
- `external`: second-model or external-AI review; only when explicitly requested.

Default is standard. Never run `external` implicitly.

## Scope prompt

When scope is missing, use `AskUserQuestion` with header `Review scope` and these options:

- Uncommitted changes.
- Branch compared to default branch.
- Specific files or PR diff supplied by the user.

## Team mode

Run sub-tasks as the read-only `reviewer` role. Split by review dimension or file group. Each sub-task must use the host skill's severity rubric and return only evidence-backed findings.

Consolidate before reporting:

- Deduplicate by `file:line` plus claim.
- Keep the highest severity only when the evidence matches the rubric.
- Move unsupported or disputed claims to Needs review.
- Prefix confirmed findings with `[Flagged by: <dimension or file group>]` only when it helps explain coverage.

## External mode

When `external` is requested, spawn configured external reviewer bridges in parallel if available. Do not depend on a specific bridge or model.

Report the result explicitly:

- `External review: completed` when it ran.
- `External review: unavailable` when no bridge exists.
- `External review: skipped` when privacy, missing scope, or tooling prevents it.

Apply the host severity rubric to external output. Do not include external claims as confirmed findings unless the local review can verify the evidence.

## Historical context

If memory search is available, query past observations for files in scope. Use it only to avoid repeating already-litigated findings. Do not treat memory as evidence for a new finding.
