# Config Review Rubric

Use this rubric for AI coding-agent configuration audits. Platform-specific files
add checks; they do not override local project rules or user intent.

## Severity

Critical:

- Security, privacy, or destructive-action risk.
- Config cannot load or points at missing required files.
- Generated output was edited while source remains stale.
- A hook, permission, sandbox, extension, or MCP server can run risky work without approval.

Important:

- Stale or unsupported keys, tool names, models, hook events, or manifest fields.
- Broad routing descriptions that can trigger the wrong skill or agent.
- Duplicate skills, agents, hooks, prompts, or package entries that create ambiguity.
- Always-loaded instructions exceed the repo's useful context budget.
- Missing validation for config that produces artifacts.

Suggested:

- Low-risk cleanup that improves clarity, token use, or maintainability.
- Optional newer features with clear benefit but no immediate correctness risk.
- Better grouping, naming, or source-to-generated documentation.

## Shared checks

### Scope and ownership

- Identify user, project, package, and generated config separately.
- Prefer source files over generated exports.
- Ask before touching private, global, or managed config.
- Keep platform-specific rules scoped to that platform.

### Context efficiency

- Keep startup context short and durable.
- Move specialized workflows into skills, commands, or prompts loaded on demand.
- Remove duplicate rules unless they deliberately enforce a critical behavior.
- Treat long instruction files as a risk only when content is low-signal or always loaded.

### Routing

- Names and descriptions must say when to use the component and when not to use it.
- Adjacent skills or agents should not share the same trigger phrases unless one delegates to the other.
- Do not route app config, git hygiene, or ordinary docs into this skill.

### Safety

- Least privilege wins for permissions, sandbox, hooks, extensions, MCP, and package installs.
- Deterministic enforcement belongs in hooks or extensions, not advisory instructions.
- Secrets must not be embedded in committed prompt, settings, or package files.
- Network, filesystem expansion, and command execution need explicit scope.

### Evidence

Every finding needs file, line, setting key, tool output, or official-doc evidence.
No evidence, no finding.

### Fix readiness

A fix is ready only when:

- the source file is known
- the change is small and reversible
- risky effects are named
- validation is available or the gap is reported
- user approval exists for fix mode
