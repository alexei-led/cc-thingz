---
{"description":"Create, split, slim, or rewrite repository skills. Use when adding a new `src/skills/\u003cname\u003e/` skill, editing a skill description, frontmatter, references, overlays, or plugin placement, or tightening routing between neighboring skills. NOT for score-only instruction review; use reviewing-instructions. NOT for broad agent/package config audits; use evolving-config. NOT for ordinary docs; use documenting-code.","name":"writing-skills"}
---

# Writing Skills

Create or reshape a skill so it loads at the right time, gives the model the
result and the finish line, and ships intact to every target. The same rules
apply to agent bodies and other AI-facing instruction files; the
reviewing-instructions skill scores against them.

Done when the skill meets the shape and writing rules below, the rendered Claude
skill still holds the base body and its reference links, and the relevant
build/test/lint checks pass on what you changed, or you name each check that did
not run and why.

Without write access, return proposed changes (file, change, reason) instead of
applying them.

## References

- `references/skill-principles.md` — read when choosing invocation mode,
  splitting or merging skills, or pruning a long skill.
- `references/repo-conventions.md` — read before touching package JSON,
  overlays, target-only tokens, generated output, or evals in this repo.

## Shape

These follow the agentskills.io specification:

- `name`: lowercase kebab-case, at most 64 characters, matching the directory.
- `description`: at most 1024 characters, saying what the skill does, when to
  use it, and what it is NOT for, naming the neighbor skill to use instead. One
  trigger per branch; no synonym piles.
- `SKILL.md` body at most 500 lines (about 5k tokens); most skills need far less.
- Conditional detail lives in `references/`, linked directly from `SKILL.md`
  with when to read it. No reference chains.
- Deterministic operations live in `scripts/`, not in prose.
- The skill is self-contained: name another skill when handing off, but do not
  link into its files.

## Writing rules

- State the result, the constraints, and what done means. Number steps only
  where order is a real constraint: safety gates, deterministic tooling, apply
  flows.
- Cut what the model already knows: language idioms, textbook debugging, what a
  commit or test is, "read the code first".
- Keep what is local, non-obvious, opinionated, version-gated, or costly to
  rediscover.
- Hard constraints are short and explicit and may be negative: secrets,
  destructive commands, prod apply, release publishing, external actions. Write
  preferences as positive statements.
- Use plain statements. Skip ALL-CAPS emphasis, "MANDATORY", and "think step by
  step / carefully"; reasoning effort is a runtime setting.
- State each rule once. The body does not restate the description's NOT-for
  list. Required checks appear once; after they pass, repeat them only after a
  change or failure.
- Name no specific model versions. Put a tier alias (`inherit`, `sonnet`,
  `haiku`) in a sidecar only where the harness needs a value.
- Headers, lists, and code blocks carry structure. Use a table when it is the
  clearest form.
- Specify an output shape only when another tool or agent parses it.
- A skill that changes code ends with the done line below instead of long
  verification or final-response sections. A skill that may run in a read-only
  role carries the read-only line.

```text
Done when the relevant build/test/lint checks pass on what you changed, or you name each check that did not run and why.
Without write access, return proposed changes (file, change, reason) instead of applying them.
```

## Overlays

Keep the base `SKILL.md` vendor-neutral. For target-only content, end the base
with a short neutral heading such as `## Platform additions` and one generic
sentence, then patch that heading from `.agentbundler/targets/<target>.json`
with `bodyPatch.mode: "sections"`. Use `mode: "replace"` only for a deliberate
full fork: it discards the whole base body, including its reference links.
`references/repo-conventions.md` has the patch mechanics.

## Output

```markdown
## Skill Change

- `path` — created | changed | proposed: <what and why>

Routing: model-invoked | user-invoked; triggers <terms>; NOT for <neighbors or none>
Checks: <check>: passed | failed | not run (<reason>)
Follow-up: <scoring run, docs update, or none>
```
