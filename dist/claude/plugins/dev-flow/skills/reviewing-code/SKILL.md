---
allowed-tools:
- Task
- TaskOutput
- TaskCreate
- TaskUpdate
- TaskList
- AskUserQuestion
- Read
- Grep
- Glob
- LS
- Bash(git *)
- Bash(gh pr *)
- Bash(gh api *)
- mcp__plugin_claude-mem_mcp-search__search
- mcp__plugin_claude-mem_mcp-search__get_observations
argument-hint: '[deep] [team] [external]'
context: fork
description: Use when reviewing changed code, PRs, diffs, or specific files. Finds
  evidence-backed defects in security, correctness, tests, reliability, performance,
  maintainability, and docs. Supports quick, standard, deep, team, and external-review
  modes. NOT for repo-wide architecture review, general codebase exploration, fixing
  issues (use fixing-code), improving tests without a code review (use improving-tests),
  or applying refactors (use refactoring-code).
name: reviewing-code
user-invocable: true
---

# Code Review

Produce findings, not edits. Review only the requested diff, PR, changed files,
or file list. If scope or diff context is missing, ask one clarifying question.

## Read first

Read `references/severity-rubric.md` before scoring or reporting findings.
Load language references only for languages present in scope:

- C#: `references/csharp.md`
- Go: `references/go.md`
- Java/Kotlin: `references/java-kotlin.md`
- Python: `references/python.md`
- Rust: `references/rust.md`
- TypeScript: `references/typescript.md`
- Web, HTML, CSS, JS, HTMX: `references/web.md`

Unsupported language: use this skill and the severity rubric only; report reduced coverage.

## Review modes

Default mode is standard unless the user asks otherwise.

Quick:

- Use for small, low-risk diffs.
- Cover security and correctness only.
- Review changed lines plus direct local context.

Standard:

- Use for normal reviews.
- Cover security, correctness, and tests.
- Review changed files plus direct callers or callees when needed to validate a finding.

Deep:

- Use when the user asks for deep, thorough, risk, or merge-safety review.
- Cover all dimensions: security, correctness, tests, reliability, performance, maintainability, and docs.
- Review changed files, relevant callers/callees, boundary inputs, and affected tests.

Team:

- Use only when the user asks for team, parallel, multi-agent, or multi-pass review.
- Split by dimension or file group, then consolidate into one report.
- Deduplicate by `file:line` plus claim. Keep the strongest severity only when evidence supports it.
- Put unresolved disagreements under Needs review, not confirmed findings.

External:

- Use only when the user explicitly asks for external, Codex, second model, or second opinion.
- Keep private code local unless the configured bridge runs locally or the user approved sharing.
- Consolidate external output with the same severity rubric. Downgrade unsupported external claims to Needs review.
- Report whether external review completed, was unavailable, or was skipped for privacy/tooling reasons.

## Scope resolution

Use the user's named scope without asking. Otherwise choose one:

- Uncommitted changes.
- Branch compared to default branch.
- Specific files or PR diff supplied by the user.

Tool-enabled role: use the matching git or PR command consistently for the whole review.
Read-only role: work from supplied diff, file list, and tool output. If that context is absent, ask for it instead of guessing.

If there are no changes in scope, report `Nothing to review.`

## Evidence gathering

For each scoped language:

1. Read the relevant language reference.
2. Inspect changed code and enough nearby code to validate claims.
3. Use supplied or runnable tooling output when available.
4. Use graph evidence only when it answers a review question, not as a default fishing pass.

GitNexus is useful for PRs, broad diffs, public API changes, and missed caller/test coverage:

- Detect changes to map changed symbols to affected flows.
- Impact analysis for non-trivial changed symbols.
- Context for changed boundary symbols, callers, callees, and tests.

codegraph is useful for dependency/call blast radius and high fan-in surfaces:

- Check status first.
- If fresh, use context or affected queries for changed symbols or files.
- Stale or partial indexes are not evidence. Refresh if allowed; otherwise report the gap.

## Review dimensions

Security:

- Auth, authorization, injection, unsafe deserialization, secrets, crypto, SSRF, XSS, CSRF, path traversal, data exposure.

Correctness:

- Logic errors, edge cases, null or empty handling, contract mismatches, broken callers, unchecked errors, migrations, API compatibility.

Tests:

- Missing regression tests, uncovered changed behavior, weak assertions, over-mocking, missing error or boundary cases.

Reliability:

- Resource leaks, retries, timeouts, cancellation, concurrency, races, idempotency, cleanup, observability for failures.

Performance:

- Realistic hot paths, unbounded work, N+1 queries, blocking I/O, memory growth, avoidable cost.

Maintainability:

- Dead code, confusing indirection, shallow wrappers, mixed responsibilities, brittle coupling, unclear invariants.

Simplicity (over-engineering):

- Reinvented stdlib or native behavior, single-implementation abstractions, factories with one product, speculative flexibility, dependencies a few lines would replace, dead flags or config.

Docs:

- Public API docs, migration notes, user-facing behavior, accessibility text, and operator docs affected by the change.

Simplify focus:

- When the user asks for a simplification, over-engineering, or "what can we delete" review, scope to the Simplicity dimension only and emit a delete-list instead of the standard template.
- One line per finding: `file:line — <tag> <what>. <replacement>.` Tags: `delete` (dead or speculative, nothing replaces it), `stdlib` / `native` (name the function or platform feature), `yagni` (one implementation, inline it), `shrink` (same logic, fewer lines).
- End with `net: -N lines possible.` Nothing to cut: `Lean already. Ship.`

## Finding rules

- Every confirmed finding needs `file:line` or quoted tool output.
- Every confirmed finding needs severity, category, confidence, scenario, and fix.
- No evidence, no finding.
- Missing context becomes Needs review, not a hedged finding.
- Do not report style or formatting already handled by project tooling unless it creates real risk.
- Keep findings scoped. List adjacent suspicious areas as out of scope instead of expanding the review.
- Security web research is only for public facts such as CVEs or official docs. Do not send private code or diffs to web tools.

## Scoring

If the user asks for a score, apply `references/severity-rubric.md` exactly:

1. Assign severity and confidence for each finding.
2. Apply caps first.
3. Apply deductions.
4. State score confidence: high, medium, or low.
5. If review coverage is partial, show the cap reason.

Do not invent precision. Use one decimal only when arithmetic needs it.

## Output

```markdown
## Code Review Summary

Scope: <description>
Depth: quick | standard | deep | team | external
Languages: <list>
Coverage: complete | partial — <reason>
Graph evidence: none | GitNexus | codegraph | both — <freshness/gaps>
External review: not requested | completed | unavailable | skipped — <reason>
Score: <N/10 if requested> — confidence <high|medium|low>

### Critical

- `file:line` — <category>, confidence <level>. <issue> Scenario: <how it fails>. Fix: <concrete fix>.

### Warnings

- `file:line` — <category>, confidence <level>. <issue> Scenario: <how it fails>. Fix: <concrete fix>.

### Suggestions

- `file:line` — <category>, confidence <level>. <improvement>. Fix: <concrete fix>.

### Needs review

- `file:line or tool/context gap` — <missing context and why it matters>.

### Summary

<2-3 sentences with merge risk and next actions. Say "No confirmed findings" when clean.>
```

Omit empty severity sections except Needs review when it explains partial coverage.

## Edge cases

- Missing diff or file list in read-only mode: ask for it.
- Tool unavailable: report the gap and continue with source review.
- Tests missing for changed behavior: report under tests with the missing behavior named.
- Large scope: review requested scope first; recommend deep/team mode for more coverage.
- Generated or vendored files: review only if the change is direct and source generation is in scope.## Platform workflow additions

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
