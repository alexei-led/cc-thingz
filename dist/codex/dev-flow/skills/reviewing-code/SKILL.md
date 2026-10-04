---
{"description":"Use when reviewing changed code, PRs, diffs, or specific files. Finds evidence-backed defects in security, correctness, tests, reliability, performance, maintainability, and docs. Supports quick, standard, deep, team, and external-review modes, plus a simplify mode for over-engineering and \"what can we delete\" reviews. NOT for repo-wide architecture review, general codebase exploration, fixing issues (use fixing-code), or improving tests without a code review (use improving-tests).","name":"reviewing-code"}
---
<!-- Codex platform guidance -->
<!-- Use this platform's installed tool names exactly for shell, file reads, and search. If a referenced helper or optional tool is unavailable, say so and continue with built-in tools. -->


# Code Review

Produce findings, not edits, for the requested diff, PR, changed files, or file
list. Read `references/severity-rubric.md` before scoring or reporting: it owns
the dimensions, severity, confidence, and score rules.

Load a language reference only when a finding needs language or framework
semantics; do not read every reference merely because that language is in scope:

- C#: `references/csharp.md`
- Go: `references/go.md`
- Java/Kotlin: `references/java-kotlin.md`
- Python: `references/python.md`
- Rust: `references/rust.md`
- TypeScript: `references/typescript.md`
- Web, HTML, CSS, JS, HTMX: `references/web.md`

Other languages: use the rubric alone; report reduced coverage if missing
language guidance limits the review.

## Scope

Use the scope the user named. Otherwise ask one question offering:

- uncommitted changes
- branch compared to the default branch
- specific files or a PR diff

Use one git or PR command for the whole review. Without command access, work
from the supplied diff and files, and ask for them if absent. No changes in
scope: report `Nothing to review.`

## Modes

Default is standard.

- **Quick**: small, low-risk diffs. Security and correctness; changed lines plus direct context.
- **Standard**: security, correctness, and tests; follow callers or callees when a finding needs them.
- **Deep**: on request for a thorough, risk, or merge-safety review. All rubric dimensions, including boundary inputs and affected tests.
- **Team**: on request for team, parallel, or multi-pass review, or offered for a large diff. Split by dimension or file group, then merge into one report: dedupe by `file:line` plus claim, keep the higher severity only when evidence supports it, and put disagreements under Needs review.
- **External**: only when the user explicitly asks for an external, second-model, or second-opinion review. Keep private code local unless the bridge runs locally or the user approved sharing. Rate external output with the same rubric; claims you cannot verify go to Needs review. Report whether it completed, was unavailable, or was skipped and why.
- **Simplify**: on request for an over-engineering or "what can we delete" review. Simplicity dimension only. Instead of the Output template, one line per finding: `file:line — <tag> <what>. <replacement>.`, with tags `delete`, `stdlib`/`native` (name the replacement), `yagni`, `shrink`. End with `net: -N lines possible.` or `Lean already. Ship.`

## Evidence

- Read enough surrounding code to prove each claim. Run the project's checks when you can; a failing check in scope is evidence.
- If a code-graph tool (GitNexus, codegraph) is installed, use it for caller, impact, and test-coverage questions on broad or public-API changes; a stale index is a coverage gap, not evidence.
- Web research is for public facts only (CVEs, official docs). Never send private code or diffs to web tools.
- Skip style that project tooling already enforces. List suspicious code outside scope as out of scope instead of widening the review.
- Review generated or vendored files only when source generation is in scope.

## Output

```markdown
## Code Review Summary

Scope: <description>
Depth: quick | standard | deep | team | external
Languages: <list>
Coverage: complete | partial — <reason>
Graph evidence: none | <tool> — <freshness/gaps>
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

<2-3 sentences: merge risk and next actions, or "No confirmed findings".>
```

Omit empty sections, except Needs review when it explains partial coverage.

## Platform additions

No target-specific additions.
