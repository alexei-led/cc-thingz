# Repo Conventions

These are the local rules for authoring skills in this repository.

## Source of truth

Edit canonical sources under `src/`.

Main paths:

- `src/skills/<name>/SKILL.md` — base skill body and shared frontmatter
- `src/skills/<name>/references/` — support markdown loaded on demand
- `src/skills/<name>/scripts/` — helper scripts copied with the skill
- `src/skills/<name>/assets/` — static support files
- `src/skills/<name>/.agentbundler/targets/<target>.json` — target overlay
- `src/.agentbundler/packages/<package>.json` — package ownership and shipping surface

Do not hand-edit `dist/`. Regenerate it from source.

## Compiler shape

Agent Bundler does this:

1. Load base `SKILL.md`.
2. Apply optional target sidecar overlay.
3. Apply target-wide composition preamble.
4. Copy regular support files and sidecar replacements.

Practical rules:

- Keep the base vendor-neutral unless a target truly needs different behavior.
- Use overlays for target differences, not for ordinary content growth.
- `targets:` is source metadata. It does not leak to emitted frontmatter.
- All enabled targets ship under package-owned paths. Gemini is retired.

## Plugin ownership

Every public skill belongs in a plugin.

When adding a skill:

1. Pick the package whose public surface best matches the new capability.
2. Add the skill asset path to `src/.agentbundler/packages/<package>.json`.
3. Check whether package metadata, README tables, and totals still read correctly.

When removing or folding a skill:

1. Remove it from the package JSON.
2. Update docs that list the public skill surface.
3. Run `agbun build --root .` so removed output disappears.

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
make build
make check
agbun check --root .
```

Guidance:

- Run instruction lint for any new or heavily rewritten skill.
- Add or update a focused Agent Bundler fixture when the new skill changes the exported skill surface.
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
