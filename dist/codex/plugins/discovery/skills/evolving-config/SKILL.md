---
description: Audit and improve AI coding-agent configuration. Use when the user wants
  to review or change Claude Code, Pi, Codex, Gemini, skill, hook, or agent configuration.
  Supports review-only audits and apply-fixes mode. NOT for writing new application
  code, fixing bugs, or any task that isn't about agent/tool configuration files.
name: evolving-config
---

# Evolving Agent Configuration

Audit config with local evidence first, then current docs or web evidence when
needed. Do not rewrite config because a blog post looked shiny. Two modes:
default audit+apply, and review-only.

## Modes

### Default: Audit + Apply

Make config changes after proving they help. Read current files before
suggesting edits. Prefer small, reversible changes. Ask before deleting or
moving private config.

### Review-Only

When the user wants a read-only config review without applying changes (e.g.
"review my config", "check my setup", "review cc config", "context review"):

1. **Discover** — scan the config surface: agent instruction files, settings,
   skills, agents, hooks, commands. Build an inventory with paths and sizes.
2. **Measure context budget** — estimate startup tokens loaded before the first
   user prompt. Flag if instruction files exceed 150 lines or ~3K tokens.
3. **Review against rubric** — read [RUBRIC.md](references/RUBRIC.md) for the
   quality dimensions. Use parallel sub-agents for independent component types
   when the review scope covers multiple areas.
4. **Present findings** — report context budget table, findings by severity
   (errors/warnings/info), cross-cutting issues, top improvements, and what's
   working well.
5. **Apply fixes** — only when the user passes `--fix`. Follow the approval
   flow in [apply-fixes.md](references/apply-fixes.md).

## Scope

Review:

- Agent instruction files (`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, platform equivalents)
- Configuration directories (`.claude/`, `.pi/`, `.codex/`, `.agents/`)
- Plugin skills, agents, hooks, commands, and generated exports
- chezmoi-managed copies when deployment is part of the request

## Audit Workflow

1. Identify the config surface and the user's goal.
2. Read current files before suggesting changes.
3. Check generated-file rules before editing generated outputs.
4. Use `looking-up-docs` for library or tool docs when syntax is uncertain.
5. Use the runtime's web tools for current public docs, release notes, or
   feature availability.
6. Prefer small, reversible changes. Ask before deleting or moving private
   config.
7. Verify with the repo's validation commands.

## Findings To Prioritize

- unsupported tool names
- stale generated docs or overlays
- duplicate skills or agents
- broad trigger descriptions that cause accidental activation
- hooks that can block safe work or hide errors
- secrets or private data in prompt/config files
- generated files edited by hand

## Failure Cases

- Config target is ambiguous (e.g., user says "my config" with multiple agents present): list all detected config surfaces and ask which to audit.
- Generated file detected (e.g., `dist/` overlay or exported skill): do not edit it; report the source path and regeneration command instead.
- Validation command fails after a proposed change: revert the change and report the failure with the exact error line.

## Output Contract

```markdown
## Config Audit

### Critical

- `path:line` — issue. Fix: action.

### Important

- `path:line` — issue. Fix: action.

### Suggested

- `path:line` — issue. Fix: action.

### Verification

- command to run
```
