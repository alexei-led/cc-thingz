# Skill Format Reference

This document describes the canonical `SKILL.md` format, the platform sidecar
pattern, per-platform overlay rules, and CC-only body markers.

All skills follow the [Agent Skills](https://agentskills.io) open standard.
Claude Code extends that standard with additional frontmatter keys (marked
**CC-only** below).

## Canonical SKILL.md

Every skill has exactly one canonical `SKILL.md`. This is the authoritative
definition and the Claude Code version — it includes all CC-only frontmatter
and MCP tool references. Overlays for other platforms are generated from it
by stripping CC-only content.

```yaml
---
name: skill-name
description: >-
  One-line trigger description used by the host to decide when to activate
  this skill. Key use case first; combined with when_to_use, capped at 1,536
  chars in the skill listing.
# CC-only frontmatter below — stripped from Codex/Gemini/Pi overlays
model: claude-sonnet-4-6 # pin model for this skill
effort: medium # low|medium|high|xhigh|max
context: fork # run in a forked subagent context
agent: Explore # subagent type when context:fork
when_to_use: | # extra trigger phrases for CC skill listing
  Triggers on "foo", "bar"
user-invocable: true # false = Claude-only, hidden from / menu
disable-model-invocation: false
argument-hint: "[issue-number]"
arguments: [issue, branch] # named positional args → $issue, $branch
paths: # only activate when editing matching files
  - "src/**/*.go"
memory: project # CC memory mode
allowed-tools: # CC authorizes these without per-call prompt
  - Read
  - Grep
  - Glob
  - Bash(gh *)
  - mcp__perplexity-ask__perplexity_ask
  - mcp__plugin_claude-mem_mcp-search__smart_search
---
```

### CC-only frontmatter keys

These keys are meaningful only in Claude Code. The overlay generator strips
them when producing Codex, Gemini, and Pi outputs.

| Key             | CC meaning                                             |
| --------------- | ------------------------------------------------------ |
| `model`         | Pin Claude model for this skill's turns                |
| `effort`        | Effort level: `low` `medium` `high` `xhigh` `max`      |
| `context`       | `fork` — run skill in an isolated subagent             |
| `agent`         | Subagent type when `context: fork`                     |
| `when_to_use`   | Extra trigger text appended to `description`           |
| `argument-hint` | Autocomplete hint, e.g. `[issue-number]`               |
| `arguments`     | Named positional args for `$name` substitution         |
| `paths`         | Glob patterns: activate only when editing these files  |
| `memory`        | CC memory mode (`project`, `user`, `local`)            |
| `hooks`         | Hooks scoped to this skill's lifecycle                 |
| `shell`         | Shell for `!` blocks: `bash` (default) or `powershell` |

### Portable frontmatter keys

These keys are understood by all platforms and must not be stripped.

| Key                        | Meaning                                          |
| -------------------------- | ------------------------------------------------ |
| `name`                     | Required. Lowercase, hyphens only, max 64 chars. |
| `description`              | Required. Used for automatic skill matching.     |
| `allowed-tools`            | Tools pre-authorized without per-call prompt.    |
| `disable-model-invocation` | `true` = user-only invocation, not automatic.    |
| `user-invocable`           | `false` = hidden from / menu, Claude-only.       |

### Allowed-tools in canonical SKILL.md

The canonical file may include `mcp__*` entries in `allowed-tools`. These are
CC-native and are stripped from all overlays. On CC, they pre-authorize MCP
tool calls for this skill without per-use permission prompts.

To pre-authorize MCP tools without editing a shared skill, add them to
`allowed-tools` in `~/.claude/settings.json` instead.

## Platform sidecar pattern

When a skill needs materially different workflow guidance on a specific
platform — not just different tool names, but a genuinely different procedure —
create a platform sidecar in the same directory as `SKILL.md`:

```
plugins/<plugin>/skills/<skill>/
├── SKILL.md          ← canonical (CC version, all CC frontmatter)
├── SKILL.pi.md       ← Pi override (only when materially different)
└── SKILL.codex.md    ← Codex override (rarely needed)
```

### When to add a sidecar

Add a sidecar only when the workflow is structurally different, not cosmetic:

| Reason for sidecar (do this)                               | Reason NOT to sidecar (let overlay strip)  |
| ---------------------------------------------------------- | ------------------------------------------ |
| Pi has native `web_answer`/`web_search` vs Perplexity MCP  | Tool names differ but steps are identical  |
| Pi uses `web_research` for async research workflows        | CC-ONLY body section covers the difference |
| Pi workflow requires fundamentally different step ordering | MCP tools simply stripped leaves the rest  |

### Sidecar frontmatter rules

`SKILL.pi.md` and `SKILL.codex.md` must not contain CC-only frontmatter keys
or `mcp__*` entries in `allowed-tools`. The overlay generator rejects them.

```yaml
# SKILL.pi.md — Pi-specific frontmatter only
---
name: researching-web
description: >-
  Web research via Pi web providers. Use for technical comparisons,
  recent facts, best practices, standards.
allowed-tools:
  - Bash(gh *)
  - Bash(ast-grep *)
  - Bash(sg *)
  - Bash(rg *)
---
```

### Overlay fallback chain

When generating platform outputs, the overlay generator uses:

1. `SKILL.pi.md` → use as-is for Pi (no stripping needed)
2. `SKILL.codex.md` → use as-is for Codex
3. `SKILL.md` → strip CC-only frontmatter keys and `mcp__*` from `allowed-tools`

If no sidecar exists, the stripped canonical is used. The generator produces:

- `flat/skills-codex/<skill>/SKILL.md` — Codex/Gemini overlay
- `flat/skills-pi/<skill>/SKILL.md` — Pi overlay

## CC-ONLY body markers

For CC-specific content inside the skill body (e.g. agent spawn examples
using CC `Task()` calls), wrap in comment markers:

````markdown
<!-- CC-ONLY: begin -->

```python
Task(subagent_type="perplexity-researcher", prompt="Research: <topic>")
```
````

<!-- CC-ONLY: end -->

````

The overlay generator strips everything between these markers (inclusive)
from Codex, Gemini, and Pi outputs. Use for:

- CC `Task()` / `Agent()` call examples
- MCP tool usage examples in skill body
- CC-specific keyboard shortcuts or slash commands

Do not use for tool-name differences that are the same workflow — use the
sidecar pattern for those.

## Pi platform guidance block

Pi sidecars must include this comment block immediately after the frontmatter
closing `---`. It tells GPT-5.5 the exact tool names available in Pi:

```markdown
<!-- Pi platform guidance -->
<!-- Use Pi tool names exactly: read, bash, edit, write, ask_user_question, structured_output, todo, Agent, get_subagent_result, steer_subagent, web_search, web_answer, web_research. -->
<!-- Use Agent, get_subagent_result, and steer_subagent for delegated work. -->
<!-- Use ctx7 or npx ctx7@latest through bash when Context7 documentation lookup is required. -->
````

This block is Pi-only. Do not include it in canonical `SKILL.md`.

## Per-platform overlay summary

| Platform    | Source file                             | CC-only keys | `mcp__` in allowed-tools | CC-ONLY body |
| ----------- | --------------------------------------- | ------------ | ------------------------ | ------------ |
| Claude Code | `SKILL.md`                              | kept         | kept                     | kept         |
| Pi Agent    | `SKILL.pi.md` or stripped `SKILL.md`    | n/a          | stripped                 | stripped     |
| Codex CLI   | `SKILL.codex.md` or stripped `SKILL.md` | n/a          | stripped                 | stripped     |
| Gemini CLI  | stripped `SKILL.md`                     | stripped     | stripped                 | stripped     |

## Dynamic context injection

CC skills support `` !`command` `` syntax to inject shell output before Claude
sees the skill content. This runs at skill load time, not during the conversation.

```markdown
## Current diff

!`git diff HEAD`
```

Pi and Codex do not support this syntax — do not use it in sidecars.

## String substitutions (CC)

| Variable               | Description                                      |
| ---------------------- | ------------------------------------------------ |
| `$ARGUMENTS`           | Full argument string as typed                    |
| `$ARGUMENTS[N]`        | Argument by 0-based index                        |
| `$N`                   | Shorthand for `$ARGUMENTS[N]`                    |
| `$name`                | Named argument from `arguments` frontmatter list |
| `${CLAUDE_SKILL_DIR}`  | Directory containing the skill's `SKILL.md`      |
| `${CLAUDE_SESSION_ID}` | Current session ID                               |
| `${CLAUDE_EFFORT}`     | Current effort level                             |

## Skill eval fixtures

Each skill can have eval fixtures at
`tests/skill-evals/<plugin>/<skill>/evals/evals.json`.

```json
{
  "skill_name": "my-skill",
  "evals": [
    {
      "id": "unique-kebab-id",
      "name": "human readable name",
      "prompt": "Prompt text sent to the skill during evaluation.",
      "expected_output": "Optional prose for human reviewers.",
      "assertions": ["The output does X.", "The output does not do Y."]
    }
  ]
}
```

Required per eval item: `id`, `name`, `prompt`, `assertions` (non-empty).

Validate by building the temporary eval tree:

```sh
uv run python scripts/evals/prepare-skill-evals.py --out /tmp/cc-thingz-skill-eval-root
```

Run full LLM evals:

```sh
make skill-evals
```

Add 3–5 prompts minimum: happy path, a boundary case, one that should route
elsewhere.

## Required CLI tools

### Runtime

| Tool       | Purpose                                 | Install                 |
| ---------- | --------------------------------------- | ----------------------- |
| `gh`       | GitHub CLI for `exploring-repos`        | `brew install gh`       |
| `ast-grep` | Structural code search before text grep | `brew install ast-grep` |
| `rg`       | Ripgrep text search                     | `brew install ripgrep`  |
| `fd`       | Fast file find                          | `brew install fd`       |
| `ctx7`     | Library docs via Context7               | `npm i -g ctx7`         |

### Development

| Tool        | Purpose                | Install                  |
| ----------- | ---------------------- | ------------------------ |
| `uv`        | Python package manager | `brew install uv`        |
| `bats-core` | Bash hook testing      | `brew install bats-core` |

## Validating config

```sh
uv run python scripts/validate/validate-config.py
```

Checks:

- Every `skills/*/SKILL.md` has `name` and `description`
- `SKILL.pi.md` and `SKILL.codex.md` sidecars contain no CC-only keys or `mcp__*`
- Pi/Codex exports contain no CC tool names (`AskUserQuestion`, `mcp__*`, etc.)
- Gemini extension references all flat skills exactly once
