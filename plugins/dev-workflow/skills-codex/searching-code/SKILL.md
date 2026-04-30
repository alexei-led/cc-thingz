---
allowed-tools:
- Read
- Grep
- Glob
description: Intelligent codebase search and zoom-out mapping via WarpGrep. Use when
  user asks "how does X work", "trace flow", "find all implementations", "understand
  codebase", "zoom out", "map this area", or needs cross-file exploration in large
  repos (1000+ files).
name: searching-code
---

<!-- Platform guidance for non-Claude models (Codex CLI, Gemini CLI) -->
<!-- Persistence: Keep going until the task is fully resolved. Do not stop at the first obstacle. -->
<!-- Tool use: Use available tools to verify — do not guess at file contents, paths, or command output. -->
<!-- Planning: Reflect between steps. Decompose complex problems into logical sub-steps before acting. -->
<!-- Reliability: Assess risk before irreversible actions. Ask for clarification on ambiguity. -->
<!-- Completeness: Generate complete responses without truncating. Review your output against the original constraints. -->

# Intelligent Code Search with WarpGrep

WarpGrep is an RL-trained search agent that reasons about code, not just pattern matches. Use zoom-out mode when the user needs a higher-level map before touching code.

## How It Works

- **8 parallel searches** per turn (explores multiple hypotheses)
- **4 reasoning turns** (follows causal chains across files)
- **F1=0.73** in ~3.8 steps (vs 12.4 for standard search)

## When to Use Which Tool

| Use WarpGrep                | Use Smart Explore (claude-mem)     | Use Built-in Grep        |
| --------------------------- | ---------------------------------- | ------------------------ |
| "How does auth flow work?"  | "What functions are in this file?" | "Find class UserService" |
| "Trace data from API to DB" | "Show me this function's source"   | Simple regex patterns    |
| "Find all error handling"   | "Find all types matching X"        | "Where is X defined?"    |
| Large repos (1000+ files)   | File structure at a glance         | Known file patterns      |
| Before major refactoring    | Targeted function extraction       | Quick needle lookups     |

**When available**, prefer Smart Explore for structural queries (10-20x fewer tokens). Use WarpGrep for semantic/reasoning queries across files.

## Query Formulation

**Good queries** (reasoning required):

```
"How does authentication flow from the login handler to the database?"
"Find all places where user permissions are checked"
"Trace the request lifecycle from router to response"
```

**Bad queries** (use Grep instead):

```
"Find UserService" → use Grep
"Search for 'import React'" → use Grep
```

## Workflow

1. **Formulate query**: Describe WHAT you want to understand, not just WHAT to find
2. **Load domain docs when present**: `CONTEXT.md`, `CONTEXT-MAP.md`, and relevant ADRs
3. **Run WarpGrep**: `mcp__morphllm__warpgrep_codebase_search`
4. **Interpret results**: Ranked snippets with file paths and line numbers
5. **Follow up**: Read specific files for deeper understanding

## Zoom-Out Mode

Use when the user says "zoom out", "map this area", "go up a layer", or sounds lost in local details.

Return a map, not a dump:

- relevant modules and callers
- data/control flow across seams
- domain terms from `CONTEXT.md`
- ADR constraints that shape the design
- where to read next, limited to the top 3 files

Avoid line-by-line explanations unless asked. The point is orientation, not drowning the user in snippets.

## Parameters

```
search_string: "natural language description of what to find"
repo_path: "/absolute/path/to/repo"
```

## Tips

- Be specific about the behavior or flow you're investigating
- Include context: "in the API layer" or "during startup"
- WarpGrep handles ambiguity better than exact pattern matching
- Results include surrounding context for understanding
