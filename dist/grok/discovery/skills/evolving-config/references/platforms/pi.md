# Pi Configuration

Use this reference when auditing Pi coding-agent setup.

## Surfaces

Check relevant user, project, and package config:

- `~/.pi/agent/settings.json`
- `.pi/settings.json`
- `~/.pi/agent/AGENTS.md`, project `AGENTS.md`, and `CLAUDE.md` fallback files
- `~/.pi/agent/skills/`, `.pi/skills/`, `.agents/skills/`
- `~/.pi/agent/extensions/`, `.pi/extensions/`
- `~/.pi/agent/mcp.json`, `.pi/mcp.json` — MCP server config, see [MCP servers](#mcp-servers)
- `~/.pi/agent/trust.json` — saved project-trust decisions
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
- `docs/mcp.md`, `docs/security.md` — MCP config and project trust

## Checks

- Project settings override global settings deliberately; nested object merge behavior is understood.
- Package entries are pinned when stability matters and filtered when only some resources should load.
- Local package paths resolve relative to the settings file that declares them.
- Skills follow Agent Skills frontmatter rules: clear `name`, specific `description`, and references loaded on demand.
- Extensions are trusted executable code, kept project-local only when the team should share them.
- Package dependencies needed at runtime are in `dependencies`; Pi core packages are peer dependencies when imported.
- Resource filters avoid loading unused skills, prompts, extensions, or themes.
- `AGENTS.md` contains durable global or repo guidance, not per-task transcripts.
- Pi-specific reality is respected: since v0.99.0 Pi has built-in MCP support (see
  [MCP servers](#mcp-servers)); subagents, plan mode, permission popups, and todos
  still need extensions or packages unless the audited install already provides them.

## MCP servers

Pi connects to MCP servers over stdio or streamable HTTP as a built-in extension
(`builtin:mcp`, added v0.99.0; source: [`docs/mcp.md`](https://github.com/earendil-works/pi/blob/v0.99.1/packages/coding-agent/docs/mcp.md)).

- Config lives in `~/.pi/agent/mcp.json` (global) or `.pi/mcp.json` (project).
  A project entry replaces a global entry with the same name. `.pi/mcp.json` is
  only read once the project is trusted (see below), because stdio servers run
  commands.
- stdio servers take `command` (a single executable, not a shell string), `args`,
  `env`, `cwd`. HTTP servers take `url`, `headers`, `oauth`; `type: sse` is
  rejected. Server names allow only letters, digits, `_`, `-`; tools are named
  `mcp__<server>__<tool>`.
- Secrets belong in `${NAME}` (env var) or `!command` (a command that prints the
  value) inside `env`/`headers`, never as literal values. Flag any inline
  token, key, or password in `mcp.json`.
- `exposure` controls how a server's tools reach the model: `direct` (declared
  like a built-in tool), `codemode`/`codemode-deferred` (callable only from
  codemode scripts), `deferred` (loaded on demand by `tool_search`), or
  `hidden`. `toolExposure` overrides it per tool, by exact name or `*` pattern —
  use it to keep destructive tools off `direct` on a large server.
  `autoEnableCodemode: false` at the top level of `mcp.json` stops Pi from
  auto-activating `codemode` for a connected server.
- OAuth tokens are stored in `~/.pi/agent/mcp-auth.json`; never quote its
  contents. Server logs go to `~/.pi/agent/mcp.log`.
- `pi mcp list` connects to every enabled server and reports state, tools, and
  connection errors — useful to recommend for an audit, but it launches stdio
  server commands, so do not run it yourself against config you have not
  reviewed. `pi mcp add|remove|login|logout` and `/mcp` manage servers without
  editing JSON by hand.
- Disable the built-in extension with `"extensions": ["-builtin:mcp"]` in
  settings (project entries of `+builtin:<name>`/`-builtin:<name>` override the
  user setting); `pi config` lists it under Built-in. An installed extension
  that registers `/mcp` (for example `pi-mcp-adapter`) silently replaces the
  built-in support — Pi then ignores `mcp.json` in sessions entirely, which is
  worth flagging if both are present.
- `defaultTools` accepts `+codemode` / `+tool_search` to keep those tools active
  without an MCP server, and `-name` to remove a default tool; plain entries
  replace the whole default list.
- cc-thingz's own `permission-gate` extension
  (`src/plugins/pi/extensions/extensions/permission-gate.ts`) confirms only the
  `bash` tool; it does not gate MCP tool calls. A server added to `mcp.json`
  runs unconfirmed unless another extension adds a `tool_call` handler for it.

### Project trust

`.pi/mcp.json` (along with `.pi/settings.json`, `.pi/extensions`, `.pi/skills`,
and related project resources) only loads after a project-trust decision;
source: [`docs/security.md`](https://github.com/earendil-works/pi/blob/v0.99.1/packages/coding-agent/docs/security.md#project-trust).
Trust does not sandbox tool calls after startup — it only gates whether these
files load at all — so a trusted project's MCP servers still run with the Pi
process's OS permissions. Decisions are saved per directory in
`~/.pi/agent/trust.json`; `defaultProjectTrust` (user-only setting) is the
fallback when no decision is saved.

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
