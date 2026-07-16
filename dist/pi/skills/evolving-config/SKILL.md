---
{"description":"Audit and improve AI coding-agent configuration. Use when reviewing or changing Claude Code, Pi, Codex, skill, agent, hook, MCP, permission, package, or generated-export setup. Default is review-only; fixes require explicit user approval or --fix. NOT for score-only instruction review or prompt lint; use reviewing-instructions. NOT for application config, git hygiene, code bugs, ordinary docs, or generated files without their source.","name":"evolving-config"}
---
<!-- Pi platform guidance -->
<!-- Use installed Pi tool names exactly. Installed extensions may add toolsets such as Task*, Monitor*, and Loop*; use the visible tool names exactly and do not translate them to Claude syntax. -->
<!-- Prefer Task* over `todo` when task-tracking tools are available; `todo` is the cc-thingz fallback. Prefer MonitorCreate for long-running or background commands and LoopCreate for scheduled or event-driven follow-up instead of Bash sleep/poll loops. -->
<!-- Use subagent for delegated work. Use wait to block on async subagent runs only when no independent work remains. -->
<!-- Use ctx7 or npx ctx7@latest through bash when Context7 documentation lookup is required. -->


# Evolving Agent Configuration

Audit AI coding-agent configuration with local evidence first and current vendor
docs second. Default to review-only. Apply fixes only after explicit approval.

## Read first

- `references/RUBRIC.md` for shared review dimensions and severity.
- `references/platforms/claude-code.md` for Claude Code surfaces.
- `references/platforms/codex.md` for Codex surfaces.
- `references/platforms/pi.md` for Pi surfaces.
- `references/apply-fixes.md` only when the user asks to fix or passes `--fix`.

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

Do not review:

- app runtime config
- git hook hygiene
- score-only instruction prose or prompt quality; use `reviewing-instructions`
- product docs
- source-code quality
- generated output as the source of truth

## Workflow

1. Identify the requested platform, config root, and mode.
2. If ambiguous, list detected config surfaces and ask which to audit.
3. Inventory relevant files with paths, sizes, and source/generated status.
4. Read current files before recommending changes.
5. Use the platform reference and shared rubric to check expected structure, high-risk settings, invocation fit, and always-loaded context cost.
6. When the audit touches skills, agents, prompts, or package manifests, inspect thin-router risk, weak pointers to must-read support files, and whether plugin grouping forces unrelated instructions into startup context.
7. Use official docs or changelogs when syntax, feature availability, or deprecation status is uncertain.
8. Use broad web research only for gaps or ecosystem comparisons; do not recommend changes from uncited blogs alone.
9. Classify findings by impact and disruption.
10. In fix mode, apply only approved changes and verify with available validation commands.

## Priorities

Flag these first:

- unsupported or stale config keys, tool names, hook events, or model names
- unsafe permissions, sandbox bypasses, broad MCP access, or secret exposure
- generated exports edited by hand instead of source files
- duplicate or overlapping skills, agents, hooks, prompts, or trigger descriptions
- model-invoked descriptions that do not earn their always-loaded cost
- thin-router skills or prompts with little independent capability
- weak pointers from entrypoints to must-read support files
- bloated startup context or plugin grouping that should be on demand
- hooks or extensions that hide errors, block safe work, or run risky commands
- missing validation for config that produces skills, agents, hooks, or packages

## Output

Use optional finding tags such as `routing/thin-router`,
`context/weak-pointer`, or `invocation/over-model-invoked` when they sharpen the
issue.

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

- `path:line` — <category[/subtype]>: <issue>. Evidence: <fact>. Fix: <action>.

### Important

- `path:line` — <category[/subtype]>: <issue>. Evidence: <fact>. Fix: <action>.

### Suggested

- `path:line` — <category[/subtype]>: <issue>. Evidence: <fact>. Fix: <action>.

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
