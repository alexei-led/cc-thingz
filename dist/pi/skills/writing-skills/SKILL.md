---
description: Create, split, slim, or rewrite repository skills. Use when adding a
  new `src/skills/<name>/` skill, editing a skill description, frontmatter, references,
  overlays, or plugin placement, or tightening routing between neighboring skills.
  NOT for score-only instruction review; use reviewing-instructions. NOT for broad
  agent/package config audits; use evolving-config. NOT for ordinary docs; use documenting-code.
name: writing-skills
---

<!-- Pi platform guidance -->
<!-- Use Pi tool names exactly: read, bash, edit, write, ask_user_question, structured_output, todo, Agent, get_subagent_result, steer_subagent, web_search, web_answer, web_research. -->
<!-- Use Agent, get_subagent_result, and steer_subagent for delegated work. -->
<!-- Use ctx7 or npx ctx7@latest through bash when Context7 documentation lookup is required. -->

# Writing Skills

Create or reshape a skill so it triggers at the right time, stays lean, and
matches this repo's source and build rules.

## Read first

- `AGENTS.md` section `## Writing Agent/Skill Instructions` for markdown signal rules.
- `references/skill-principles.md` for invocation, description, disclosure, split,
  and pruning rules.
- `references/repo-conventions.md` for `src/skills/`, plugin manifests, overlays,
  generated outputs, and verification.
- `src/skills/reviewing-instructions/references/scoring-rubric.md` only after the
  draft exists and quality needs a final check.

## Use this skill for

- creating a new skill
- rewriting a skill body or description
- splitting one skill into a skill plus references
- splitting one skill into two skills when the trigger or workflow boundary is real
- merging or extending overlapping skills after checking the neighboring skills
- pruning bloated skill prose, duplicate rules, or weak trigger phrasing
- adding target overlays or support files to a skill

## Do not use this skill for

- scoring or linting prompt files without editing them; use `reviewing-instructions`
- broad agent, hook, extension, MCP, or package audits outside skill authoring;
  use `evolving-config`
- ordinary docs, READMEs, or code comments; use `documenting-code`
- external library or API lookup; use `looking-up-docs`
- broad design debate before a concrete skill change exists; use
  `brainstorming-ideas`

## Workflow

1. Find the source of truth under `src/skills/<name>/`. Read the owning
   `src/plugins/*/plugin.yaml` and the closest neighboring skills before editing.
   Treat `dist/` as generated.
2. State the smallest correct shape:
   - edit the current skill
   - move conditional detail to `references/`
   - add a target overlay
   - split into two skills
   - merge or fold into a neighboring skill
3. Decide invocation mode and trigger surface.
   - Model-invoked: use when the agent or another skill must discover it on its
     own.
   - User-invoked: use when it is mostly a manual expert tool or reference.
   - Keep one trigger per branch. Name real neighboring skills when overlap is
     possible. Put the NOT-clause in the description, not as an afterthought.
4. Keep the main body for the common path only: scope, steps, output contract,
   failure handling, and the few rules every run needs.
5. Move conditional detail down:
   - `references/` for extra rules, examples, or domain detail
   - `<target>/frontmatter.yaml` for target-specific frontmatter
   - `<target>/body.md` for target-specific body changes
   - `<target>/references/`, `scripts/`, or `assets/` for target-specific support
6. Tighten wording until each line changes behavior. Delete generic agent advice,
   duplicated rules, and pretty prose.
7. When adding or removing a public skill, update the owning
   `src/plugins/<plugin>/plugin.yaml`. Update `AGENTS.md` and `README.md` when
   they expose the public skill surface or counts.
8. Before claiming done, run the narrowest verification that proves the new skill
   compiles and reads well.
9. If quality is still uncertain, run `reviewing-instructions` on the new or
   changed skill and apply the highest-value fixes.

## Writing rules

- Bias toward predictability over style.
- Prefer headers, bullets, numbered steps, and short imperative lines.
- Keep each meaning in one place.
- Inline only what every trigger path needs.
- Use references for detail that only some branches need.
- Add an output contract when the skill produces findings, plans, edits, or
  artifacts.
- Add failure handling for ambiguous scope, missing inputs, generated files,
  unavailable tools, and verification gaps.
- Do not create a new skill just to rename an existing trigger.
- Do not add a target overlay when a vendor-neutral base already works.

## Output

Write-capable role:

```markdown
## Skill Update

Updated:

- `path` — <created or changed>

Plugin:

- <plugin name or unchanged>

Routing:

- Invocation: model-invoked | user-invoked
- Trigger surface: <main trigger terms>
- Excludes: <neighbor skills or none>

Verified:

- <check>: passed | skipped (<reason>)

Follow-up:

- <reviewing-instructions run, docs update, or none>
```

Read-only role:

```markdown
## Proposed Skill Change

Files:

- `path`

Why:

- <routing, disclosure, or repo-convention reason>

Proposed shape:

- Invocation: model-invoked | user-invoked
- Plugin: <plugin>
- References or overlays: <list or none>

Patch summary:

- <small bullet list of edits>
```

## Failure handling

- Ambiguous request between new skill and neighbor-skill edit: ask one scoped
  question before editing.
- Existing skill already covers the job: prefer tightening or extending it over
  adding a duplicate.
- Plugin ownership is unclear: list the plausible plugins and ask which public
  surface the user wants.
- Generated files differ from source: edit `src/` first, then regenerate.
- Build or compile check is unavailable: report the exact gap and do not claim
  generated outputs are current.
- A target needs unique behavior everywhere: add an overlay only after the
  vendor-neutral base fails.
