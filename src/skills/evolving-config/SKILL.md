---
description:
  Audit and improve AI coding-agent configuration. Use when reviewing or changing
  Claude Code, Pi, Codex, skill, agent, hook, MCP, permission, package, or
  generated-export setup. Default is review-only; fixes require explicit user
  approval or --fix. NOT for application config, git hygiene, code bugs, ordinary
  docs, or generated files without their source.
name: evolving-config
---

# Evolving Agent Configuration

Audit AI coding-agent configuration with local evidence first and current vendor
docs second. Default to review-only. Apply fixes only after explicit approval.

## Read first

- `references/RUBRIC.md` for shared review dimensions and severity.
- `references/platforms/claude-code.md` for Claude Code surfaces.
- `references/platforms/codex.md` for Codex surfaces.
- `references/platforms/pi.md` for Pi surfaces.
- `references/apply-fixes.md` only when the user asks to fix or passes `--fix`.

No dedicated Gemini coverage. If the user explicitly asks for Gemini config,
review local files only and state that current best-practice coverage is skipped.

## Modes

Review-only is the default for prompts such as "review my config", "audit
config", "check setup", or "what should I improve".

Fix mode starts only when the user explicitly asks for changes or passes `--fix`.
Even in fix mode, ask before risky changes: permissions, sandbox policy, hooks,
MCP servers, model routing, deletes, moves, broad rewrites, or private config.

## Scope

Review these AI-agent configuration surfaces:

- Instruction files: `AGENTS.md`, `CLAUDE.md`, command prompts, skill and agent bodies.
- Claude Code: `.claude/`, user/project/local settings, hooks, skills, agents, MCP, permissions.
- Codex: `.codex/`, `~/.codex/config.toml`, project config, profiles, sandbox, approvals, MCP, skills, subagents.
- Pi: `.pi/`, `~/.pi/agent/`, settings, packages, skills, extensions, prompts, themes, context files.
- Plugin/package manifests and source-to-generated export rules.
- chezmoi or dotfile copies only when deployment is part of the request.

Do not review app runtime config, git hook hygiene, product docs, source-code
quality, or generated output as the source of truth.

## Workflow

1. Identify the requested platform, config root, and mode.
2. If ambiguous, list detected config surfaces and ask which to audit.
3. Inventory relevant files with paths, sizes, and source/generated status.
4. Read current files before recommending changes.
5. Use the platform reference to check expected structure and high-risk settings.
6. Use official docs or changelogs when syntax, feature availability, or deprecation status is uncertain.
7. Use broad web research only for gaps or ecosystem comparisons; do not recommend changes from uncited blogs alone.
8. Classify findings by impact and disruption.
9. In fix mode, apply only approved changes and verify with available validation commands.

## Priorities

Flag these first:

- unsupported or stale config keys, tool names, hook events, or model names
- unsafe permissions, sandbox bypasses, broad MCP access, or secret exposure
- generated exports edited by hand instead of source files
- duplicate or overlapping skills, agents, hooks, prompts, or trigger descriptions
- bloated startup context or always-loaded instructions that should be on demand
- hooks or extensions that hide errors, block safe work, or run risky commands
- missing validation for config that produces skills, agents, hooks, or packages

## Output

```markdown
## Config Audit

Scope: <platforms/files>
Mode: review-only | fix-approved
Sources: <local files and docs checked>
Confidence: high | medium | low

### Summary

- Files reviewed: N
- Generated files skipped: N
- Main risk: <one sentence>

### Critical

- `path:line` — issue. Evidence: <fact>. Fix: <action>.

### Important

- `path:line` — issue. Evidence: <fact>. Fix: <action>.

### Suggested

- `path:line` — issue. Evidence: <fact>. Fix: <action>.

### Working Well

- <config that should stay as-is>

### Verification

- <command run or recommended>
```

Omit empty severity sections. If no findings are confirmed, say `No confirmed
findings.`

## Failure handling

- Ambiguous target: ask one scoped question before auditing.
- Missing official docs: use local evidence, lower confidence, and report the gap.
- Generated file target: report the source path and regeneration command instead of editing it.
- Secrets or private data: do not quote secret values; identify only the path and key name when needed.
- Validation failure after a fix: revert the change unless the user asks to keep it, then report the exact error.
