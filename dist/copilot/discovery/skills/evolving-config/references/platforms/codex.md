# Codex Configuration

Use this reference when auditing OpenAI Codex CLI setup.

## Surfaces

Check relevant user and project config:

- `~/.codex/config.toml`
- `.codex/config.toml`
- `~/.codex/<profile>.config.toml`
- system config when visible, such as `/etc/codex/config.toml`
- `AGENTS.md` files in the repo tree
- MCP server definitions
- skills, prompts, and custom agent or subagent definitions when present

## Official docs to prefer

- Best practices: `https://developers.openai.com/codex/learn/best-practices`
- Config basics: `https://developers.openai.com/codex/config-basic`
- Config reference: `https://developers.openai.com/codex/config-reference`
- Approvals and security: `https://developers.openai.com/codex/agent-approvals-security`
- Subagents: `https://developers.openai.com/codex/subagents`

## Checks

- User config holds personal defaults; project config holds repo-specific behavior and loads only for trusted projects.
- Profiles are explicit modes, not dumping grounds for unrelated overrides.
- Sandbox mode and approval policy are conservative by default and loosened only for trusted workflows.
- Network access and workspace-write expansion have a clear reason.
- `AGENTS.md` is short, durable, and focused on repo workflow, tests, tools, constraints, and done criteria.
- MCP servers are intentional, trusted, and use environment variables or secret managers for credentials.
- Skills encode stable repeatable workflows; experimental behavior stays out of durable config.
- Subagents have specific roles and inherit safe sandbox and approval assumptions.

## Common fixes

- Move one-off experiments to CLI flags or temporary profiles.
- Tighten sandbox, approval, or network settings for untrusted repos.
- Split bloated `AGENTS.md` guidance into skills or task-specific prompts.
- Remove stale profiles, duplicated MCP servers, and unsupported keys after checking the current reference.
