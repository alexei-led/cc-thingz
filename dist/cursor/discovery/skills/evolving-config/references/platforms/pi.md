# Pi Configuration

Use this reference when auditing Pi coding-agent setup.

## Surfaces

Check relevant user, project, and package config:

- `~/.pi/agent/settings.json`
- `.pi/settings.json`
- `~/.pi/agent/AGENTS.md`, project `AGENTS.md`, and `CLAUDE.md` fallback files
- `~/.pi/agent/skills/`, `.pi/skills/`, `.agents/skills/`
- `~/.pi/agent/extensions/`, `.pi/extensions/`
- prompt templates, themes, and package manifests
- installed git or npm package specs in settings
- `package.json` `pi` manifests for local packages

## Local docs to prefer

When available in this repo or installation, read Pi docs before web research:

- `README.md`
- `docs/settings.md`
- `docs/skills.md`
- `docs/extensions.md`
- `docs/packages.md`
- `docs/models.md`
- `docs/prompt-templates.md`

## Checks

- Project settings override global settings deliberately; nested object merge behavior is understood.
- Package entries are pinned when stability matters and filtered when only some resources should load.
- Local package paths resolve relative to the settings file that declares them.
- Skills follow Agent Skills frontmatter rules: clear `name`, specific `description`, and references loaded on demand.
- Extensions are trusted executable code, kept project-local only when the team should share them.
- Package dependencies needed at runtime are in `dependencies`; Pi core packages are peer dependencies when imported.
- Resource filters avoid loading unused skills, prompts, extensions, or themes.
- `AGENTS.md` contains durable global or repo guidance, not per-task transcripts.
- Pi-specific reality is respected: no built-in MCP, subagents, plan mode, permission popups, or todos unless extensions or packages provide them.

## Common fixes

- Move private package paths, sessions, or model defaults to user settings.
- Use package object filters to disable unneeded resources.
- Replace generated or exported files with edits to source package files plus rebuild.
- Add `npmCommand` when package installs must run through a Node version manager.
- Use `/reload`-friendly extension locations for active local extension development.
