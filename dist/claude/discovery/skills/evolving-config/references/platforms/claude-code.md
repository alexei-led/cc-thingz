# Claude Code Configuration

Use this reference when auditing Claude Code setup.

## Surfaces

Check relevant user, project, local, and managed config:

- `~/.claude/settings.json`
- `.claude/settings.json`
- `.claude/settings.local.json`
- `CLAUDE.md`, `.claude/CLAUDE.md`, `~/.claude/CLAUDE.md`, local memory files
- `.claude/skills/*/SKILL.md`
- `.claude/agents/*.md`
- `.claude/commands/**/*.md`
- hook scripts referenced from settings
- MCP server definitions and related environment variables

## Official docs to prefer

- Settings: `https://docs.anthropic.com/en/docs/claude-code/settings`
- Hooks: `https://docs.anthropic.com/en/docs/claude-code/hooks`
- Skills: `https://docs.anthropic.com/en/docs/claude-code/skills`
- Subagents: `https://docs.anthropic.com/en/docs/claude-code/sub-agents`
- MCP: `https://docs.anthropic.com/en/docs/claude-code/mcp`

## Checks

- Settings hierarchy is intentional: user for personal defaults, project for shared repo behavior, local for uncommitted personal overrides, managed for enforced policy.
- Permissions are least-privilege. Broad allow rules, dangerous bash patterns, network access, and secret paths need explicit justification.
- Hooks are deterministic, reviewed as executable code, and scoped to exact events and matchers.
- Skills are focused, have precise descriptions, and put rare detail in references.
- Subagents have single responsibilities, clear tool limits, and concise output contracts.
- MCP servers are explicit and trusted; avoid enabling every project server by default.
- Memory files contain durable, repo-wide guidance rather than task transcripts or tutorial prose.

## Common fixes

- Move personal or secret settings from project files to local/user scope.
- Replace advisory must-run rules in `CLAUDE.md` with hooks when deterministic enforcement is required.
- Split broad skills or agents by trigger and responsibility.
- Trim stale model names, deprecated keys, and duplicate permission entries after verifying docs.
