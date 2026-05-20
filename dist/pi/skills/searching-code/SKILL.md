---
description: Intelligent codebase search with AST-first local search and zoom-out
  mapping. Use when user asks "how does X work", "trace flow", "find all implementations",
  "understand codebase", "zoom out", "map this area", structural code-pattern search,
  or cross-file exploration in large repos. Try ast-grep before rg for code-shape
  queries; use WarpGrep for semantic flow.
name: searching-code
---

<!-- Pi platform guidance -->
<!-- Use Pi tool names exactly: read, bash, edit, write, ask_user_question, structured_output, todo, Agent, get_subagent_result, steer_subagent, web_search, web_answer, web_research. -->
<!-- Use Agent, get_subagent_result, and steer_subagent for delegated work. -->
<!-- Use ctx7 or npx ctx7@latest through bash when Context7 documentation lookup is required. -->

# Codebase Search in Pi

Map code with verified file references. Do not read the whole repo because the
user sounds curious. Curiosity is not a query plan.

## Search Tool Order

1. `ast-grep` / `sg` for structural code patterns.
2. `rg` for exact text, strings, comments, docs, logs, and config keys.
3. `fd` for file and directory discovery.
4. `Agent` with `reviewer` for compressed multi-file context when the search is
   broad.
5. `grep` / `find` only when modern tools are unavailable.

## Workflow

1. Clarify scope if the request is vague.
2. Check for domain docs first when present:
   - `CONTEXT.md`
   - `CONTEXT-MAP.md`
   - nearest `*/CONTEXT.md`
   - `docs/adr/*.md`
3. Classify the search:
   - Structural code shape → `ast-grep run` or `ast-grep scan`.
   - Exact text or config keys → `rg`.
   - File names or extensions → `fd`.
4. Read only the files or line ranges needed to verify the map.
5. For large searches, launch one bounded `Agent` with `reviewer` to gather
   compressed context. Keep the main loop in control.
6. Separate verified facts from guesses and unknowns.

## Useful Commands

```bash
command -v ast-grep || command -v sg
ast-grep run --pattern 'console.log($$$)' --lang javascript .
ast-grep scan --inline-rules 'id: await-in-func
language: javascript
rule:
  kind: function_declaration
  has:
    pattern: await $EXPR
    stopBy: end
' .
rg -n 'login|authenticate|AuthService|Session|UserRepository'
fd 'auth|login|session|user'
```

Use `sg` in place of `ast-grep` if that is the installed binary.

## Zoom-Out Mode

Use when the user says "zoom out", "map this area", "go up a layer", or sounds
lost in local details.

Return:

1. Flow with `file:line` references.
2. Key modules and responsibilities.
3. Callers, callees, shared types, and messages.
4. Unknowns or unverified assumptions.
5. Read-next list, top 3 files only.

For structural searches, include the ast-grep pattern or rule used.

## Output Contract

```markdown
## Code Map

### Scope

<what was mapped>

### Flow

1. `path:line` — fact
2. `path:line` — fact

### Modules

- `module/path` — responsibility and key files

### Search

- `<command or rule>` — why it was used

### Unknowns

- <gap and how to verify>

### Read Next

1. `path` — why
```
