---
description:
  Audit AI coding-agent configuration against current features and local
  usage. Use when the user wants to improve Claude Code, Pi, Codex, Gemini, skill,
  hook, or agent configuration. NOT for writing new application code, fixing bugs,
  or any task that isn't about agent/tool configuration files. NOT for review-only
  audits without applying changes (use `reviewing-cc-config`).
name: evolving-config
---

# Evolving Agent Configuration

Audit config with local evidence first, then current docs or web evidence when
needed. Do not rewrite config because a blog post looked shiny. That way lies
confetti architecture.

## Scope

Review:

- `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`
- `.claude/`, `.pi/`, `.codex/`, `.agents/`
- plugin skills, agents, hooks, commands, and generated exports
- chezmoi-managed copies when deployment is part of the request

## Workflow

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
