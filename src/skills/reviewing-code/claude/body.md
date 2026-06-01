# Code Review

## Workflow (\_+)

Track progress through the workflow phases using `TaskCreate` / `TaskUpdate`.

If `$ARGUMENTS` is passed, the keywords below tune the workflow:

- `deep` — cover all six review dimensions, not just the security and correctness pair.
- `team` — fan the dimensions to parallel reviewer sub-tasks that challenge each other's findings and converge.
- `external` — additionally spawn external AI reviewers. Only when explicitly requested; never run by default.

Without `external`, run only this skill's own review. Never spawn external reviewers implicitly.

## Determine scope (\_+)

Use `AskUserQuestion` with header "Review scope" and the three options spelled out above.

## Review dimensions (\_+)

Run the dimensions as the read-only `reviewer` role. For large scope, the orchestrator may fan them out as parallel `Task(subagent_type="reviewer", prompt=...)` sub-tasks, one per dimension or per file group; each sub-task's model is set in its own metadata — do not pin a model from the skill.

When `team` is set, run those sub-tasks as an agent team so they challenge each other's findings; the report prefixes each finding with `[Flagged by: <dimension>]`.

When `external` is set, additionally spawn any configured external-AI reviewer bridges in parallel for a second-model pass on security and quality. Do not hard-depend on a specific external agent; skip silently if none is configured.

## Historical context (optional) (\_+)

If `mcp__plugin_claude-mem_mcp-search__search` is available, query for past findings on the files in scope:

```text
search({ query: "<file paths in review scope>", limit: 10 })
```

Fetch full observations via `get_observations` for relevant hits. Skip already-litigated issues. Skip silently if the MCP is not installed.
