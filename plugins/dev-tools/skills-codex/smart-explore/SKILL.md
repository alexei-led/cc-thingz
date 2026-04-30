---
description: Token-efficient code navigation via AST parsing. Use when exploring file
  structure, cross-file symbol discovery, or targeted function extraction with smart_outline,
  smart_search, and smart_unfold. 10-20x fewer tokens than reading full files.
name: smart-explore
---

<!-- Platform guidance for non-Claude models (Codex CLI, Gemini CLI) -->
<!-- Persistence: Keep going until the task is fully resolved. Do not stop at the first obstacle. -->
<!-- Tool use: Use available tools to verify — do not guess at file contents, paths, or command output. -->
<!-- Planning: Reflect between steps. Decompose complex problems into logical sub-steps before acting. -->
<!-- Reliability: Assess risk before irreversible actions. Ask for clarification on ambiguity. -->
<!-- Completeness: Generate complete responses without truncating. Review your output against the original constraints. -->

# Smart Explore: AST-Based Code Navigation

Use these tools **when available** (requires claude-mem plugin). Fall back to Read/Grep/Glob if unavailable.

## When to Use Which

| Task                          | Tool            | Tokens    |
| ----------------------------- | --------------- | --------- |
| File structure at a glance    | `smart_outline` | ~1,500    |
| Cross-file symbol discovery   | `smart_search`  | ~3,500    |
| Read a specific function/type | `smart_unfold`  | ~400-2100 |
| Simple string search          | Grep            | varies    |
| Full file needed              | Read            | ~8,000+   |

## Progressive Disclosure Workflow

1. **Outline first**: `smart_outline` shows every function/class/interface with bodies collapsed
2. **Search if needed**: `smart_search` finds symbols across files by concept
3. **Unfold targeted**: `smart_unfold` extracts exact function source by AST node — never truncates
4. **Read only if needed**: Fall back to Read for files where AST parsing isn't useful

## Key Advantages

- **AST-based extraction** guarantees complete function bodies (no truncation)
- **Structural views** show all symbols without reading full file content
- **Predictable cost**: 1 tool call per operation, consistent token ranges
- **Composable**: outline → search → unfold chain naturally
