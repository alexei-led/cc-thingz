---
{"allowed-tools":["Read","Grep","Glob","Task","Bash(uv run python src/skills/reviewing-instructions/scripts/lint-instructions.py *)"],"context":"fork","description":"Use when asked to lint, audit, review, or score AI-facing instruction files such as SKILL.md, AGENT.md, AGENTS.md, CLAUDE.md, platform body.md files, prompt files, rules, policies, and agent-facing references. NOT for plugin manifests, application code review, harness configuration review, ordinary docs, tests, or generated build output.\n","name":"reviewing-instructions","user-invocable":true}
---

# Instruction Review

Score AI-facing instruction files and report findings an author can act on. The
target style: outcome and done criteria up front, each rule stated once, hard
constraints explicit, nothing the model already knows, portable across agent
targets. The writing-skills skill teaches the same style to authors.

Done when every in-scope file has a score, a cited reason per dimension, caps
applied, and a confidence level, and every finding quotes or locates its
evidence.

## References

- `references/scoring-rubric.md` — dimensions, bands, caps, confidence, and
  defect labels. Read for every review.
- `references/model-context.md` — read when the target names a model family or
  the user passes `--model`. Default context is generic.
- `references/calibration.md` — read when a score is borderline, confidence is
  low, or you are comparing two versions.

## Scope

- Input is a file, a directory, or a skill or agent name. A bare name expands to
  `src/skills/<name>` or `src/agents/<name>.md`.
- For one file, review that file unless the user asks for linked files. For a
  directory, review its entrypoint plus the support files it links or contains.
- With no scope, list likely entrypoints (SKILL.md, AGENT.md, AGENTS.md,
  CLAUDE.md, body.md, prompt and rules files) and ask one question before
  reviewing more than one skill, agent, or package.
- Package JSON is routing evidence only; manifest review belongs to
  evolving-config.
- Put ambiguous candidates under Candidates Not Reviewed with the reason.

## Pre-pass

When a shell is available, run the advisory linter on the scope:

```bash
uv run python src/skills/reviewing-instructions/scripts/lint-instructions.py <scope>
```

Confirm or dismiss each warning during review; the rubric decides. If the script
cannot run, record `Structural pre-pass: skipped (<reason>)` and continue.

## Review

Judge each file against its own job: a read-only reviewer needs different limits
than an apply flow, and a reference file needs no routing description. Pick the
band first, apply caps, and name the top one to three improvements by impact.
Flag ambiguous actors, referents, overloaded terms, and missing conditions
when they change behavior. Judge concision by preserved meaning, not word count.
Local project rules win over vendor guidance; report the conflict. For repeated
scoring or reranking, keep the scope, model context, and rubric version fixed.

## Output

```markdown
## Instruction Review Report

Model context: <family or generic> — source <source>
Rubric version: <date>
Review confidence: high | medium | low

### Summary

- Files reviewed: N
- Candidates not reviewed: N
- Structural pre-pass: <confirmed and dismissed warnings, or skipped reason>
- Score range: X-Y / 10
- Main risk: <one sentence>

### Scores

path/to/file.md — overall X / 10, confidence <high|medium|low>

- Caps: none | capped at N because <reason>
- Outcome and Done: X — <evidence>
- Routing: X — <evidence>
- Consistency: X — <evidence>
- Hard Constraints: X — <evidence>
- Concision: X — <evidence>
- Progressive Disclosure: X — <evidence>
- Portability: X — <evidence>

### Findings

1. path:line — <high|medium|low> <dimension[/label]>: <issue>. Evidence: <quote>. Fix: <change>.

### Top Improvements

1. <highest-impact change>

### Candidates Not Reviewed

- path — <reason>
```

Omit empty optional sections. When no findings survive the evidence check,
`No confirmed findings.` replaces only the Findings section; Summary and the
per-file Scores with evidence stay.

## Platform additions

### Arguments

From `$ARGUMENTS`: the first non-flag token is the scope; `--model <name>`
overrides model context; `--team` fans out review tasks for large scopes;
`--rerank` compares two versions per `references/calibration.md`.

### Parallel review

Review one file or one small skill folder directly. For several independent
files or packages, run at most 3 Task reviewers at once, batched by sorted path.
Give each the exact file list, the resolved model context, the path to
`references/scoring-rubric.md`, and the evidence rule.

When results return, drop out-of-scope files, recompute caps a task skipped, and
deduplicate findings by file plus dimension. If two scores differ by more than 1
point, compare caps first; report unresolved disagreements as low-confidence
notes instead of averaging.
