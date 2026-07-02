---
description: Use when reviewing changed code, PRs, diffs, or specific files. Finds
  evidence-backed defects in security, correctness, tests, reliability, performance,
  maintainability, and docs. Supports quick, standard, deep, team, and external-review
  modes. NOT for repo-wide architecture review, general codebase exploration, fixing
  issues (use fixing-code), improving tests without a code review (use improving-tests),
  or applying refactors (use refactoring-code).
name: reviewing-code
---

<!-- Pi platform guidance -->
<!-- Use Pi tool names exactly: read, bash, edit, write, ask_user_question, structured_output, todo, Agent, get_subagent_result, steer_subagent, web_search, web_answer, web_research. -->
<!-- Use Agent, get_subagent_result, and steer_subagent for delegated work. -->
<!-- Use ctx7 or npx ctx7@latest through bash when Context7 documentation lookup is required. -->

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

Security, correctness, tests, reliability, performance, maintainability,
simplicity (over-engineering), and docs. Scope and coverage checklist per
dimension: `references/severity-rubric.md`.

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
- Generated or vendored files: review only if the change is direct and source generation is in scope.
