---
description:
  Intelligent codebase search with AST-first local search and zoom-out mapping. Use when
  user asks "how does X work", "trace flow", "find all implementations", "understand
  codebase", "zoom out", "map this area", structural code-pattern search, or cross-file
  exploration in large repos. Try ast-grep before rg for code-shape queries; use WarpGrep
  for semantic flow.
name: searching-code
---

# Intelligent Code Search

Use the cheapest tool that answers the question with verified file references.
For code structure, that means ast-grep before text search. For semantic flow,
that means targeted entry points first, then WarpGrep or another semantic search.
Do not read the whole repo because the user sounds curious. Curiosity is not a
query plan.

## Search Tool Order

1. `ast-grep` / `sg` — code structure: language constructs, call shapes,
   functions containing or missing code, AST-aware refactor candidates.
2. `rg` — exact text: strings, comments, docs, logs, config keys, unknown
   identifiers where structure is irrelevant.
3. `fd` — file and directory discovery.
4. WarpGrep / semantic search — multi-hop code flow and architecture questions
   after entry points are known.
5. `grep` / `find` — only when modern tools are unavailable.

## Critical Workflow Rules

- Classify the query first: structural code search, text search, file discovery,
  or semantic flow. Do not blindly start with `rg`.
- For structural code searches, test ast-grep on a small pattern or inline rule,
  then run it on the scoped tree.
- For trace-flow and architecture questions, read domain docs first when
  present: `CONTEXT.md`, `CONTEXT-MAP.md`, nearest `*/CONTEXT.md`, and relevant
  `docs/adr/*.md` files.
- Do not read the whole repo indiscriminately. Convert vague asks into a scoped
  map question or ask for scope.
- Trace callers, callees, shared types/messages, and data/control flow across
  files. Follow only enough files or line ranges to verify the map.
- Separate known facts from guesses. List unknowns explicitly instead of filling
  gaps.
- For vague requests like "read this repo and explain everything", refuse the
  full dump, offer a zoom-out map, and say the final summary will separate
  verified facts from guesses/unknowns.

## ast-grep Quick Use

Check the executable. Prefer `ast-grep`; use `sg` if that is what the system has.

```bash
command -v ast-grep || command -v sg
```

Pattern search:

```bash
ast-grep run --pattern 'console.log($$$)' --lang javascript .
ast-grep run --pattern 'func $NAME($$$) { $$$ }' --lang go .
ast-grep run --pattern 'def $NAME($$$): $$$' --lang python . --json
```

Relational or composite rule search:

```bash
ast-grep scan --inline-rules 'id: async-without-try
language: javascript
rule:
  all:
    - kind: function_declaration
    - has:
        pattern: await $EXPR
        stopBy: end
    - not:
        has:
          pattern: try { $$$ } catch ($E) { $$$ }
          stopBy: end
' .
```

Debug pattern parsing:

```bash
ast-grep run --pattern 'class $NAME { $$$BODY }' --lang javascript --debug-query=pattern
ast-grep run --pattern 'class User { constructor() {} }' --lang javascript --debug-query=cst
```

Rule authoring details live in `references/ast-grep-rule-reference.md`.

## When to Use Which Tool

ast-grep:

- "Find all async functions without try/catch."
- "Find calls to `foo($A, $B)` inside class methods."
- "Find React components that call `useEffect` with an empty dependency list."
- "Find handlers that return errors without wrapping."
- Structural rewrite candidate mapping.

`rg`:

- "Find the string `NEXT_PUBLIC_API_URL`."
- "Search docs for OpenAI."
- "Find TODO comments."
- "Where is `UserService` mentioned?" when node shape does not matter.

WarpGrep / semantic search:

- "How does auth flow work?"
- "Trace data from API to DB."
- "Find all places where permissions are checked" when naming is inconsistent.
- Large repos where the answer requires multi-hop reasoning.

Smart Explore after narrowing:

- "What functions are in this file?"
- "Show me this function's source."
- "Extract these 3 symbols from the files the code map found."

## Query Formulation

### Good semantic-flow queries

```text
How does authentication flow from the login handler to the database?
Find all places where user permissions are checked.
Trace the request lifecycle from router to response.
```

### Good structural queries

```text
Find async functions that await without try/catch.
Find calls to oldClient.query($$$) outside repository classes.
Find React components that use useEffect and setState.
```

### Plain text queries

```text
Find UserService mentions. → use rg unless AST shape matters.
Search for import React. → use rg.
Find TypeScript files. → use fd.
```

## Workflow

For trace-flow requests, explicitly say you will first check for `CONTEXT.md`,
`CONTEXT-MAP.md`, nearest `*/CONTEXT.md`, and `docs/adr/*.md` when present
before naming domain concepts.

1. Classify the ask: structural pattern, exact text, file discovery, or semantic
   flow.
2. Load domain docs when present: `CONTEXT.md`, `CONTEXT-MAP.md`, nearest
   `*/CONTEXT.md`, and relevant ADRs.
3. Run the first local search:
   - Structural: `ast-grep run` or `ast-grep scan`.
   - Text: `rg -n 'literal|symbol|route'`.
   - Files: `fd 'auth|login|session|user'`.
4. Run semantic code search for multi-hop flow: WarpGrep or another available
   semantic search tool.
5. Read specific files or line ranges only when needed for verification.
6. Return a bounded code map with file paths and line references.

## Zoom-Out Mode

Use when the user says "zoom out", "map this area", "go up a layer", or sounds
lost in local details.

Return a map, not a dump:

- relevant modules and callers
- data/control flow across seams
- domain terms from `CONTEXT.md`
- ADR constraints that shape the design
- known facts vs guesses/unknowns
- where to read next, limited to the top 3 files

Avoid line-by-line explanations unless asked. The point is orientation, not
making paste soup.

## Final Answer Contract

Return a bounded code map:

1. Flow with `file:line` references.
2. Key modules and responsibilities.
3. Callers/callees and shared types/messages.
4. Unknowns or unverified assumptions.
5. Read-next list, top 3 files only.

For structural searches, also include the ast-grep pattern or rule used.

## Failure Handling

- ast-grep missing: report it and fall back to `rg` / `fd` only for the parts
  they can answer. Suggest `brew install ast-grep`, `npm install -g @ast-grep/cli`,
  or `cargo install ast-grep`.
- ast-grep no matches: simplify the rule, debug the parsed pattern, verify a
  target snippet exists with `rg`, then report the gap without inventing
  results.
- WarpGrep unavailable: fall back to ast-grep for structural entry points,
  `rg`/`fd` for text/file searches, and Read for specific files; say which tool
  is being used.
- Request too vague: refuse the full dump, offer a zoom-out map scoped to a
  specific module or flow, and ask for a narrowing constraint.
- No results found: broaden the query, check alternate naming conventions, or
  report the gap explicitly. Never fabricate results.
