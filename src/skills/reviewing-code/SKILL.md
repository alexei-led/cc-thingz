---
name: reviewing-code
description: Code review covering security, quality, tests, implementation, documentation, and architecture / module-depth. Use when the user asks to review code, check changes, audit a PR or diff, find refactoring opportunities, or look for shallow modules and over-abstraction. NOT for fixing the issues found (use fixing-code) or applying refactors (use refactoring-code).
---

# Code Review

Review changed code for security, quality, test coverage, and architecture. Ground every finding in concrete evidence: a `file:line` reference or tool output.

If a task-tracking facility is available, track these phases as tasks.

## Role and output contract

This skill produces findings, not edits. It owns the tiered-findings output contract below. Emit the findings regardless of role; route the actual fixes to `fixing-code` or the refactor to `refactoring-code`. A reviewer (read-only) cannot run `git diff` or builds — work from the files in scope plus any diff context the caller supplies, and ask for that context if it is missing rather than guessing.

## Workflow

1. Determine review scope.
2. Detect languages and load the matching references.
3. Walk the review dimensions across the scope. Use ast-grep before `rg` for structural code-pattern checks when Bash is available; use `rg` for exact text.
4. Aggregate findings by severity and report.

## Determine scope

Resolve the scope from the request. Options:

- Uncommitted changes
- Branch compared to the default branch
- Specific files (user provides paths)

If a role with Bash is running this, resolve to the appropriate git invocation and use it consistently across phases. If a read-only role is running this, work from the file list and diff context the caller provides. If the user already named a scope, use it without asking; otherwise ask one clarifying question.

## Detect languages and load references

Scan the changed-file extensions. For each language present, load the matching reference for language-specific review checks:

- Go → [references/go.md](references/go.md)
- Python → [references/python.md](references/python.md)
- TypeScript → [references/typescript.md](references/typescript.md)
- Web / HTML / CSS / JS → [references/web.md](references/web.md)

Mixed languages: load each matching reference. Unknown or unsupported language: use the generic dimensions below only and note the reduced coverage.

## Review dimensions

Walk every dimension across the scope. For a standard review, cover the security and correctness dimensions; for a thorough review, cover all six. If the runtime supports parallel sub-tasks and the scope is large, the orchestrator may fan the dimensions out, but the rubric is identical either way.

- Logic, security, OWASP, race conditions, unchecked errors, resource leaks
- Patterns, conventions, stdlib usage, error handling (the language reference sharpens this)
- Test coverage, edge cases, mocking discipline
- Requirements match, dependency injection, edge cases
- Comments, docstrings, API docs (ARIA labels for web)
- Over-abstraction, dead code, pass-throughs

## Review rules

- Cite concrete `file:line` evidence or tool output for every finding. No evidence, no finding.
- Findings include severity and a concrete fix.
- For security findings, remind the user: keep private code local; do not paste private diffs into web tools. Use web only for external facts (CVE, library docs); cite separately.
- Read relevant `CONTEXT.md`, `CONTEXT-MAP.md`, and `docs/adr/` before naming architecture findings. If a candidate contradicts an ADR, flag only when the friction justifies reopening the decision.
- Ask one clarifying question at a time; do not batch.

## Architecture vocabulary

When the user asks for architecture focus, use the shared module-depth terms (module, interface, seam, adapter, depth, leverage, locality), the deletion test, and the seam rule from [references/architecture-vocab.md](references/architecture-vocab.md). Findings must use that vocabulary.

## Historical context (optional)

If cross-session memory tooling is available, query for prior observations on the files about to be reviewed. Skip already-litigated issues so old findings are not repeated. Skip silently if no such tooling is configured.

## Report format

```markdown
## Code Review Summary

**Scope**: <description>
**Languages**: <list>

### Critical (must fix)

- `file:line` — issue. Fix.

### Warnings (should fix)

- `file:line` — issue. Fix.

### Suggestions (consider)

- `file:line` — improvement.

### Architecture opportunities (if requested)

- Candidate: `module`. Problem: shallow / pass-through / fake seam. Deepening move: <how>. Test benefit: <how>.

### Summary

Overall assessment in 2-3 sentences, then a prioritized list of recommended actions.
```

## Writing style

- One sentence per finding. No preamble, no "I noticed that…".
- Cut hedging: "potential", "might", "consider". State what is wrong.
- Direct: "This leaks memory" not "This could potentially lead to memory issues".
- Technical precision: include type names, function signatures, line numbers.

## Edge cases

- No changes in scope → "Nothing to review."
- Linters missing or unrunnable (read-only role) → say so explicitly; still review by reading.
- Tests missing → flag as a finding under the test-coverage dimension.
- Scope larger than expected → review only what was asked; list adjacent suspicious files as out of scope.
