---
{"allowed-tools":["Task","TaskOutput","TaskCreate","TaskUpdate","TaskList","AskUserQuestion","Read","Grep","Glob","LS","Bash(git *)","Bash(gh pr *)","Bash(gh api *)"],"argument-hint":"[quick|deep] [team] [external]","context":"fork","description":"Use when reviewing changed code, PRs, diffs, or specific files. Finds evidence-backed defects in security, correctness, tests, reliability, performance, maintainability, and docs. Supports quick, standard, deep, team, and external-review modes. NOT for repo-wide architecture review, general codebase exploration, fixing issues (use fixing-code), improving tests without a code review (use improving-tests), or applying refactors (use refactoring-code).","name":"reviewing-code","user-invocable":true}
---

# Code Review

Produce findings, not edits, for the requested diff, PR, changed files, or file
list. Read `references/severity-rubric.md` before scoring or reporting: it owns
the dimensions, severity, confidence, and score rules.

Load a language reference only for languages in scope:

- C#: `references/csharp.md`
- Go: `references/go.md`
- Java/Kotlin: `references/java-kotlin.md`
- Python: `references/python.md`
- Rust: `references/rust.md`
- TypeScript: `references/typescript.md`
- Web, HTML, CSS, JS, HTMX: `references/web.md`

Other languages: use the rubric alone and report reduced coverage.

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
- **Simplify**: on request for an over-engineering or "what can we delete" review. Simplicity dimension only. One line per finding, `file:line — <tag> <what>. <replacement>.`, with tags `delete`, `stdlib`/`native` (name the replacement), `yagni`, `shrink`. End with `net: -N lines possible.` or `Lean already. Ship.`

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

### Arguments

`$ARGUMENTS` may combine a depth (`quick` or `deep`) with `team` and `external`. Default is standard; never run `external` unless it is named.

### Claude tools

- Missing scope: ask with `AskUserQuestion`, header `Review scope`, offering the three scope options above.
- Track phases with `TaskCreate` and `TaskUpdate` on reviews longer than a few steps.
- Team mode: run each sub-task as the read-only `reviewer` agent with the rubric and its dimension or file group.
- External mode: run configured external reviewer bridges in parallel; depend on no specific bridge or model.
- If memory search is available, check past observations for files in scope only to avoid re-raising settled findings; memory is never evidence for a new finding.
