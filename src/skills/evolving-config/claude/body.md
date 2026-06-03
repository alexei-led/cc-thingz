# Evolving Agent Configuration

Audit AI coding-agent configuration with local evidence first. Default to
review-only. Apply fixes only when the user explicitly asks or passes `--fix`.

## Claude tool use

- Use Read, Glob, and Grep for local inventory.
- Use WebFetch for official docs, changelogs, and exact source URLs.
- Use Perplexity only when official docs do not answer a current best-practice or ecosystem question.
- Use AskUserQuestion before ambiguous scope or risky fixes.
- Do not fetch broad web advice before reading local config.

## Read first

- `references/RUBRIC.md` for shared review dimensions and severity.
- `references/platforms/claude-code.md` for Claude Code surfaces.
- `references/platforms/codex.md` for Codex surfaces.
- `references/platforms/pi.md` for Pi surfaces.
- `references/apply-fixes.md` only in approved fix mode.

No dedicated Gemini coverage. If the user explicitly asks for Gemini config,
review local files only and state that current best-practice coverage is skipped.

## Modes

Review-only is the default for prompts such as "review my config", "audit
config", "check setup", or "what should I improve".

Fix mode starts only when the user explicitly asks for changes or passes `--fix`.
Even then, ask before changing permissions, sandbox policy, hooks, MCP servers,
model routing, package installs, deletes, moves, broad rewrites, private config,
or managed settings.

## Workflow

1. Identify platform, config root, and mode.
2. If scope is ambiguous, list detected surfaces and ask which to audit.
3. Inventory relevant files with paths, sizes, and source/generated status.
4. Read current files before recommending changes.
5. Check the matching platform reference.
6. Fetch official docs only when syntax, feature availability, or deprecation status is uncertain.
7. Use broader web research only for source gaps or ecosystem comparisons.
8. Classify findings by impact and disruption.
9. In fix mode, apply only approved changes and verify.

## Scope

Review AI-agent config only:

- Claude Code settings, `CLAUDE.md`, skills, agents, commands, hooks, MCP, permissions.
- Codex config, `AGENTS.md`, profiles, sandbox, approvals, MCP, skills, subagents.
- Pi settings, packages, skills, extensions, prompts, themes, context files.
- Plugin/package manifests and source-to-generated export rules.

Do not review app runtime config, git hook hygiene, product docs, source-code
quality, or generated output as the source of truth.

## Priorities

Flag these first:

- unsafe permissions, sandbox bypasses, broad MCP access, or secret exposure
- unsupported or stale keys, tool names, hook events, or model names
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
