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

## Current pi-subagents

- Keep one `model` per agent override or watchdog scope. Current single-model
  releases reject `fallbackModels` in agents, overrides, and watchdog settings;
  even empty arrays fail.
- In merge-based dotfiles, delete stale keys from existing settings as well as
  desired defaults. Check user and project scopes; regenerate package assets from
  source rather than editing installed exports.
- Another model requires an explicit new launch, not resume or an automatic
  fallback chain. First inspect the failed run, confirm it stopped, and reconcile
  partial writes and external actions. Keep the task's permissions and isolation.
- Use the owning workflow/controller for retries. Do not bypass a failed workflow
  with a CLI or retry configuration/loader failures on another model.

## Common fixes

- Move private package paths, sessions, or model defaults to user settings.
- Use package object filters to disable unneeded resources.
- Replace generated or exported files with edits to source package files plus rebuild.
- Add `npmCommand` when package installs must run through a Node version manager.
- Use `/reload`-friendly extension locations for active local extension development.
