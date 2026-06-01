# Smart Explore in Pi

Use cheap local structure before reading large files. The goal is a tight outline
or exact extraction from a known area, not repo-wide codebase search.

## Boundary

Use this skill for:

- known-file outlines
- known-module outlines
- bounded symbol lookup
- exact function, method, class, or type extraction
- read-next ranges after another search/review tool narrowed the area

Do not use this skill for repo-wide structural patterns, ast-grep rules,
trace-flow, "how does X work", zoom-out maps, all-callers searches, codegraph,
GitNexus, or architecture evidence. Use a dedicated repo-wide search or
architecture-analysis workflow first; return here only after the scope is a known
file, module, or symbol.

## Tool Order

1. Language-native outline tools when available.
2. `rg` for exact text or symbol fallback in a bounded scope.
3. `fd` for candidate file discovery when the path is missing.
4. `read` after narrowing.

## Workflow

1. Confirm the scope is a known file, known module, or bounded symbol. If not,
   use a dedicated repo-wide workflow first.
2. Use `fd` only to find candidate files or language roots.
3. Use `rg` for imports, declarations, and exact symbol text inside the bounded
   scope.
4. Use language-native tools when available:
   - Python: `python -m ast`, `ruff`, `pyright`
   - Go: `go list`, `go test`, `go doc`, `gofmt -w` only when editing
   - TypeScript: `tsc --noEmit`, `bun test`
5. Read only relevant ranges or small files.
6. Return an outline with exact paths and line references.

## Commands

```bash
fd '\.(go|py|ts|tsx|js|jsx)$' src
rg -n 'class |def |func |export |interface |type ' src/module
rg -n 'UserService|createUser' src/module
```

## Output Contract

```markdown
## Smart Explore

### Scope

<known file/module/symbol>

### Files

- `path` — why it matters

### Symbols

- `path:line` — symbol and role

### Edges

- caller -> callee or import relationship

### Read Next

1. `path:line-range` — reason
```
