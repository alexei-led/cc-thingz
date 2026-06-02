# Skills Audit — 2026-05-17

## Status

Tier 1–3 executed 2026-05-17 via `docs/plans/20260517-skills-consolidation.md`
(45 → 43 skills; folds, progressive-disclosure extraction, boundary tightening; +1 from context7-cli/looking-up-docs re-split post-execution).
Tier 4 (`dev-tools` 18-skill split) remains the open decision — a breaking
marketplace change deferred for an explicit owner call.

Later cleanup removed `watch-team` and `ccgram-messaging`. A 2026-06-02
follow-up kept `looking-up-docs` as the only public docs skill and demoted
Context7 CLI mechanics to references under it. This file remains a historical
snapshot of the 2026-05-17 audit.

45 skills, 9 plugins. Verdict: the set is already mature. Every aggressive consolidation
hypothesis (one `writing-code`, merge search skills, collapse `spec-*`, merge the infra
trio) was tested against body content and rejected with evidence — the prior agent
consolidation and the NOT-clause discipline already removed the easy duplication. The
real wins are narrow: 3 skills fold into a neighbor, ~1,400 body lines move to
conditionally-loaded references, ~6 routing-boundary fixes, and one structural
problem — `dev-tools` is an 18-skill grab-bag. Mean instruction quality 7.5/10
(range 5.2–8.5). This audit made no changes; see the paired plan for execution.

## Scoring rubric

Eight dimensions, 0–10, weighted per `src/skills/reviewing-instructions/references/scoring-rubric.md`:
Signal Density 15%, Scope Specificity 15%, Output Structure 15%, Failure Handling 15%,
Format Efficiency 10%, Grounding Discipline 10%, Routing Precision 10%, Progressive
Disclosure 10%. Structural lint (`lint-instructions.py`) ran clean: 2 warnings, 21
cosmetic infos across 48 files.

## Full scores (45 skills, worst first)

Columns: SD Signal Density, SS Scope Specificity, OS Output Structure, FH Failure
Handling, FE Format Efficiency, GD Grounding, RP Routing Precision, PD Progressive
Disclosure, L body lines.

| Skill | SD | SS | OS | FH | FE | GD | RP | PD | L | Overall |
|---|---|---|---|---|---|---|---|---|---|---|
| looking-up-docs | 4 | 7 | 7 | 5 | 8 | 7 | 8 | 5 | 89 | **5.2** |
| deploying-infra | 5 | 6 | 8 | 8 | 6 | 6 | 7 | 4 | 232 | **6.1** |
| analyzing-usage | 7 | 8 | 8 | 6 | 6 | 7 | 8 | 3 | 224 | **6.2** |
| spec-core | 7 | 7 | 6 | 5 | 9 | 5 | 7 | 9 | 70 | **6.5** |
| using-cloud-cli | 5 | 7 | 4 | 8 | 7 | 7 | 7 | 5 | 209 | **6.5** |
| refactoring-code | 6 | 7 | 7 | 7 | 8 | 7 | 8 | 6 | 175 | **6.8** |
| spec-new | 8 | 8 | 8 | 5 | 9 | 6 | 7 | 9 | 66 | **6.8** |
| using-modern-cli | 6 | 7 | 5 | 6 | 8 | 6 | 7 | 8 | 82 | **7.0** |
| spec-work | 7 | 8 | 8 | 8 | 7 | 7 | 8 | 3 | 306 | **7.1** |
| grill-me | 8 | 7 | 8 | 7 | 9 | 6 | 6 | 8 | 54 | **7.1** |
| spec-init | 7 | 8 | 8 | 7 | 8 | 6 | 8 | 7 | 138 | **7.2** |
| reviewing-cc-config | 7 | 8 | 8 | 8 | 7 | 8 | 8 | 6 | 202 | **7.3** |
| documenting-code | 7 | 8 | 7 | 6 | 9 | 7 | 8 | 9 | 90 | **7.3** |
| spec-plan | 7 | 9 | 9 | 7 | 8 | 7 | 8 | 4 | 240 | **7.3** |
| exploring-repos | 7 | 8 | 9 | 8 | 8 | 7 | 7 | 9 | 71 | **7.4** |
| ccgram-messaging | 7 | 8 | 8 | 7 | 8 | 7 | 8 | 7 | 149 | **7.4** |
| spec-interview | 7 | 9 | 9 | 8 | 8 | 7 | 8 | 5 | 207 | **7.4** |
| managing-infra | 8 | 8 | 7 | 7 | 7 | 7 | 8 | 9 | 118 | **7.5** |
| evolving-config | 8 | 7 | 8 | 8 | 9 | 7 | 7 | 9 | 73 | **7.5** |
| spec-status | 8 | 8 | 9 | 7 | 8 | 8 | 8 | 8 | 103 | **7.5** |
| writing-typescript | 7 | 8 | 6 | 8 | 8 | 7 | 8 | 6 | 208 | **7.5** |
| improve-codebase-architecture | 8 | 8 | 8 | 7 | 8 | 7 | 8 | 8 | 138 | **7.6** |
| writing-go | 7 | 8 | 6 | 8 | 8 | 7 | 9 | 7 | 191 | **7.6** |
| spec-done | 8 | 8 | 8 | 8 | 9 | 8 | 8 | 8 | 99 | **7.6** |
| watch-team | 8 | 7 | 8 | 8 | 9 | 7 | 7 | 9 | 76 | **7.6** |
| writing-python | 7 | 8 | 6 | 8 | 8 | 7 | 9 | 6 | 196 | **7.7** |
| searching-code | 8 | 8 | 8 | 8 | 7 | 8 | 8 | 7 | 121 | **7.8** |
| parsing-documents | 8 | 8 | 8 | 8 | 8 | 7 | 8 | 7 | 128 | **7.8** |
| brainstorming-ideas | 7 | 8 | 8 | 5 | 8 | 7 | 8 | 7 | 152 | **7.8** |
| researching-web | 8 | 8 | 9 | 8 | 9 | 8 | 7 | 9 | 67 | **8.0** |
| writing-web | 8 | 9 | 7 | 8 | 8 | 7 | 9 | 8 | 130 | **7.9** |
| committing-code | 9 | 8 | 8 | 8 | 9 | 7 | 8 | 9 | 67 | **7.9** |
| learning-patterns | 8 | 9 | 9 | 8 | 8 | 9 | 8 | 6 | 182 | **7.9** |
| debating-ideas | 8 | 9 | 9 | 8 | 8 | 9 | 8 | 7 | 139 | **7.9** |
| testing-e2e | 8 | 8 | 9 | 8 | 9 | 8 | 8 | 9 | 85 | **7.9** |
| improving-tests | 8 | 9 | 8 | 7 | 8 | 8 | 9 | 9 | 143 | **8.0** |
| playwright-skill | 9 | 8 | 7 | 8 | 9 | 8 | 8 | 9 | 68 | **8.0** |
| fixing-code | 9 | 8 | 9 | 9 | 8 | 9 | 8 | 7 | 165 | **8.1** |
| smart-explore | 9 | 9 | 8 | 8 | 8 | 7 | 8 | 9 | 41 | **8.1** |
| using-git-worktrees | 8 | 8 | 7 | 9 | 8 | 8 | 8 | 8 | 104 | **8.1** |
| reviewing-code | 9 | 8 | 9 | 8 | 9 | 9 | 8 | 9 | 124 | **8.2** |
| mem-history | 9 | 8 | 8 | 8 | 9 | 8 | 8 | 9 | 53 | **8.2** |
| sequential-thinking | 9 | 8 | 9 | 8 | 8 | 9 | 8 | 7 | 131 | **8.3** |
| context7-cli | 9 | 9 | 8 | 9 | 9 | 9 | 7 | 8 | 100 | **8.3** |
| reviewing-instructions | 9 | 9 | 9 | 8 | 9 | 8 | 9 | 9 | 95 | **8.5** |

Overalls are agent-computed and run slightly below a strict weight calculation; they
are consistent with each other, so relative ranking is sound. Use them for ordering,
not as absolute grades.

## Cross-cutting findings

### 1. The problem is routing ambiguity and inlined reference material, not duplication

No two skills do the same job. Literal trigger-phrase collision across all 45
descriptions: zero — the NOT-clause discipline works. What hurts is (a) conceptual
trigger overlap on words like "review", "config", "plan" that the descriptions only
partially disambiguate, and (b) heavy skills inlining reference material that should
be conditionally loaded. This mirrors finding #1 of the agent audit: the dominant
problem is routing, not token bloat.

### 2. Always-loaded cost is already tight; the lever is body-on-trigger

Skill descriptions total ~2,800 tokens loaded every session (45 × ~62 words). Removing
3 skills saves ~150 tokens (-5%) — modest, because the description pool is disciplined.
The large lever is per-invocation: 7 skills inline reference material and blow past the
180/220-line thresholds (`spec-work` 306, `deploying-infra` 232, `analyzing-usage` 224,
`spec-plan` 240, `using-cloud-cli` 209, `spec-interview` 207, `reviewing-cc-config` 202).
These score 3–5 on Progressive Disclosure. Moving the reference detail out saves
~1,400 body lines on trigger, with the four heaviest skills shedding 40–60%.

### 3. Three skills are folds, not standalone skills

`looking-up-docs` (5.2, lowest) self-describes as "thin router: delegate all work to
context7-cli" — ~60% body duplication of `context7-cli`, no independent capability
beyond trigger vocabulary. `grill-me` (54 lines) has its trigger already absorbed by
`brainstorming-ideas` Step 2 and is already invoked as a sub-protocol by
`improve-codebase-architecture`. `spec-core` (6.5) is a pure dispatch shim whose tool
allowlist is a strict subset of `spec-status` and whose Overview duplicates it verbatim;
git history shows no unique capability added since the spec split.

### 4. `dev-tools` is an 18-skill grab-bag

Its description ("Modern CLI tools, git worktrees, docs lookup, research, and
brainstorming") does not describe its contents. Installing it loads 18 skill
descriptions regardless of which the user wants. This is the single biggest user-facing
cognitive-complexity and always-loaded-context problem, and it is structural, not
per-skill. `analyzing-usage` is semantically misgrouped there (it is agent cost-ops,
not a developer tool); `ccgram-messaging` and `watch-team` (in `dev-workflow`) share
the same agent-ops flavor.

### 5. Vocabulary is duplicated verbatim across the review/architecture pair

`reviewing-code` and `improve-codebase-architecture` carry the same module-depth
glossary (Module, Interface, Seam, Adapter, Depth, Leverage, Locality, the Deletion
test, the Seam rule) word-for-word. Functionally distinct workflows; the duplication
is a shared-reference candidate, not a merge.

### 6. Output-structure gaps in command/codegen skills

`using-cloud-cli` (OS 4, worst single dimension in the repo) ends mid-workflow with no
output template. The four `writing-*` skills score OS 6–7 — no response-format contract
for generated code. These are quality gaps, not consolidation targets.

## Consolidation map

### Tier 1 — fold (high confidence, low risk): 45 → 42 skills

- Superseded 2026-06-02: keep `looking-up-docs` as the public docs skill. Fold
  Context7 CLI mechanics into `looking-up-docs/references/`, then broaden the
  workflow with official ecosystem docs, Perplexity-backed source discovery, and
  GitHub version fallback. Saves 1 public skill without losing ctx7 mechanics.
- Drop `grill-me` as a skill. Move the protocol to
  `brainstorming-ideas/references/grill-protocol.md`; `improve-codebase-architecture`
  keeps working by loading that reference. Removes trigger ambiguity with
  `debating-ideas`. Saves 1 skill, 1 description.
- Drop `spec-core` as a skill. Fold its dispatch logic into `spec-status`; move the
  specctl command reference to `spec-status/references/specctl-commands.md`; add a
  `## Pipeline` section to `spec-status`. Saves 1 skill, 1 description. No capability
  lost (read-only status + dispatch already in `spec-status`).

### Tier 2 — body slimming via progressive disclosure (no merges; largest token lever)

- `spec-work` 306 → ~210: `references/implementation-modes.md`,
  `references/capture-learnings.md`.
- `deploying-infra` 232 → ~130: extract Step 3 validation checklists to references;
  dedupe safety prose against `managing-infra`.
- `using-cloud-cli` 209 → ~80: move Error Handling to existing `references/GCP.md`
  and `references/AWS.md`; add an output template.
- `analyzing-usage` 224 → ~110: Views 1–11 and jq patterns to `references/ccusage.md`.
- `spec-plan` 240 → ~205: `references/planning-rules.md`.
- `spec-interview` 207 → ~150: `references/question-categories.md`.
- `reviewing-cc-config` 202 → ~177: Phase 5 (`--fix`) to a conditionally loaded
  reference.
- `writing-{go,python,typescript,web}`: extract the boilerplate (stdlib-first, flat
  control flow, explicit error handling, no-destructive-commands,
  verify-generated-code) out of each body into that skill's own
  `references/principles.md`; ~45–55 lines off each body. The win is body slimming —
  the four bodies, not the reference. Do not merge the skills (see rejected
  hypotheses). The compiler copies `references/` per-skill only (verified in
  `scripts/build/overlay.py:apply_support_files`); there is no cross-skill include, so
  the file is owned per-skill, not a single shared file. Acceptable: references load
  on-trigger and these four never co-trigger (extension-scoped).
- `reviewing-code` + `improve-codebase-architecture`: lift the duplicated module-depth
  glossary out of both bodies into each skill's own `references/architecture-vocab.md`
  (same content, per-skill copy). Body-level dedup is the goal; the two skills rarely
  trigger together so on-trigger reference duplication costs nothing.
- `refactoring-code` 175 → ~155: trim the Architecture Deepening vocabulary block.

### Tier 3 — boundary tightening (kills routing ambiguity)

- `reviewing-cc-config` Agent 2: add "do not score instruction prose — defer to
  `reviewing-instructions`".
- `evolving-config` ↔ `reviewing-cc-config`: mutual NOT-clauses (improve+apply vs
  review-only).
- `documenting-code`: explicitly exclude ADRs (route to `learning-patterns`, which
  already routes doc edits back).
- `spec-plan` description: tighten the "idea text" path against `brainstorming-ideas`
  and `spec-interview`.
- `mem-history`: add "see also `learning-patterns`" (read/write halves of one system).
- Add missing output templates: `using-cloud-cli`, `using-git-worktrees`, engineer-mode
  output for `managing-infra`. Add failure handling to `spec-new`, `brainstorming-ideas`.

### Tier 4 — structural grouping (decision required; touches marketplace + dist rebuild)

Split `dev-tools` into coherent installable units so users load only what they want:

- thinking-tools: `brainstorming-ideas`, `debating-ideas`, `sequential-thinking`
- agent-config: `evolving-config`, `reviewing-cc-config`, `reviewing-instructions`,
  `learning-patterns`, `mem-history`, `analyzing-usage`
- docs-research: `looking-up-docs`, `researching-web`, `exploring-repos`
- cli-utils: `using-modern-cli`, `using-git-worktrees`, `parsing-documents`,
  `smart-explore`

This is the highest-leverage move for "reduce filled context" if users install
selectively, but it is a breaking marketplace change. Recommended as a decision, not
auto-executed.

## Rejected hypotheses (decisions, not omissions)

- One `writing-code` skill replacing the four `writing-*`: rejected. Per-file-extension
  auto-activation cannot carry per-language behavior in a single skill body; the
  language references diverge >90%. Only shared-boilerplate extraction is warranted.
- `searching-code` + `smart-explore` merge: rejected. The semantic (WarpGrep) vs
  structural (AST) axis is load-bearing and the skills cross-reference correctly.
- Full `spec-*` collapse: rejected. Per-skill tool allowlists differ materially
  (`spec-work` has ~20 tools incl. Agent/git/make/gh; `spec-status` is read-only);
  collapsing forces union privilege escalation. Deliberate, recently hardened design.
  Only `spec-core` folds.
- `testing-e2e` + `playwright-skill` merge: rejected. Workflow vs primitive-library
  layering is sound; merging mixes abstraction levels and worsens every dimension.
- `managing-infra` / `deploying-infra` / `using-cloud-cli` merge: rejected. Distinct
  roles (patterns / execute-validate-apply / cloud CLI). Only dedupe the safety prose.
- `fixing-code` / `refactoring-code` / `improving-tests` merge: rejected. Distinct
  workflows (diagnosis / MorphLLM batch edits / test design); only the verify tail is
  shared, which is a cross-cutting concern.

## Ranked recommendations

1. Tier 1 folds — three skills removed, zero capability lost. Highest
   value-to-risk.
2. Tier 2 progressive-disclosure extraction — the real token win; mechanical and
   low-risk; brings 7 skills under the line thresholds.
3. Tier 3 boundary tightening — small edits, directly attack the cognitive-complexity
   the user named.
4. Tier 4 `dev-tools` split — largest user-facing context reduction, but a breaking
   change; needs an explicit decision.

## Notes

Analysis only; no files changed. Per-skill detail (overlaps, verdicts, hypothesis
evidence) lives in the cluster reports that produced this synthesis. Execution is
specified in `docs/plans/20260517-skills-consolidation.md`.
