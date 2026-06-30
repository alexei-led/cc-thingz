# Repo Conventions

These are the local rules for authoring skills in this repository.

## Source of truth

Edit canonical sources under `src/`.

Main paths:

- `src/skills/<name>/SKILL.md` — base skill body and shared frontmatter
- `src/skills/<name>/references/` — support markdown loaded on demand
- `src/skills/<name>/scripts/` — helper scripts copied with the skill
- `src/skills/<name>/assets/` — static support files
- `src/skills/<name>/<target>/frontmatter.yaml` — target-only frontmatter
- `src/skills/<name>/<target>/body.md` — target-only body overlay or full replacement
- `src/plugins/<plugin>/plugin.yaml` — plugin ownership and shipping surface

Do not hand-edit `dist/`. Regenerate it from source.

## Compiler shape

The skill compiler does this:

1. Load base `SKILL.md`.
2. Honor optional `targets:` restriction.
3. Merge target frontmatter overlay.
4. Apply target body overlay.
5. Inject target preamble where applicable.
6. Copy `references/`, `scripts/`, and `assets/`, then layer target overrides.

Practical rules:

- Keep the base vendor-neutral unless a target truly needs different behavior.
- Use overlays for target differences, not for ordinary content growth.
- `targets:` is source metadata. It does not leak to emitted frontmatter.
- Claude and Codex skills ship under plugin-owned paths. Gemini and Pi ship to
  flat target paths.

## Plugin ownership

Every public skill belongs in a plugin.

When adding a skill:

1. Pick the plugin whose public surface best matches the new capability.
2. Add the skill name to `src/plugins/<plugin>/plugin.yaml`.
3. Check whether the plugin description, README plugin table, and totals still
   read correctly.

When removing or folding a skill:

1. Remove it from the plugin manifest.
2. Update docs that list the public skill surface.
3. Regenerate outputs so removed dist artifacts disappear.

## Public docs to keep aligned

When a skill becomes public, rename changes, or counts change, check:

- `AGENTS.md`
- `README.md`
- generated outputs after `make build`

Update only the docs touched by the changed public surface. Do not write a broad
marketing pass.

## Verification

Use the narrowest proof that the change works.

Useful checks:

```bash
uv run python src/skills/reviewing-instructions/scripts/lint-instructions.py src/skills/<name>
uv run pytest tests/test_compile_*.py -q
make build
make check
```

Guidance:

- Run instruction lint for any new or heavily rewritten skill.
- Add or update a focused compile test when the new skill changes the exported
  skill surface.
- Run `make build` when generated outputs must stay committed.
- Run `make check` when you need drift detection for generated artifacts.

## Routing against sibling skills

Check nearby skills before creating a new one.

In this repo, common neighbors are:

- `reviewing-instructions` — scores or critiques instruction files
- `documenting-code` — updates docs, including agent-facing docs
- `evolving-config` — audits agent config and shipping surfaces broadly
- `brainstorming-ideas` — clarifies or debates a plan before implementation
- `looking-up-docs` — gets external docs for tool, API, or platform questions

If the new behavior is mostly one of those with a small twist, tighten the
existing skill instead of adding a new one.

## Default bias

Prefer this order:

1. tighten an existing skill
2. move detail to references
3. add a small target overlay
4. create a new skill

Create a new skill only when the routing boundary and the workflow both earn it.
