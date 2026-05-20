---
description:
  Token-efficient local code navigation and extraction. Use when exploring a known
  file or bounded module outline, finding a known symbol in a scoped area, or extracting
  exact function/type bodies with smart_outline, smart_search, and smart_unfold. NOT
  for repo-wide structural pattern search, "how does X work", trace-flow, zoom-out
  maps, or ast-grep rule searches — use searching-code.
name: smart-explore
---

# Smart Explore: Local Code Navigation

Use cheap structure before reading large files. The goal is precise outline and
extraction from a known area, not repo-wide search theater.

## Boundary

Use this skill for:

- known-file outlines
- known-module outlines
- targeted symbol lookup in a bounded scope
- exact function, class, method, or type extraction
- read-next ranges after a code map already narrowed the area

Do not use this skill for:

- repo-wide structural pattern search — use `searching-code`
- ast-grep rule authoring or code-shape queries — use `searching-code`
- semantic flow, architecture, or "how does X work" — use `searching-code`
- broad "find all implementations/callers in the repo" — use `searching-code`

## Tool Order

1. `smart_outline` for known files or modules.
2. `smart_search` for a known symbol or concept in a bounded scope.
3. `smart_unfold` for exact function/type source.
4. `rg` for exact text fallback when smart tools are unavailable.
5. `fd` for candidate file discovery when the file path is missing.
6. Read full files only when smaller structural views are insufficient.

## When to Use Which

- File structure at a glance — `smart_outline`.
- Bounded symbol discovery — `smart_search`.
- Specific function/type body — `smart_unfold`.
- Simple string fallback — `rg`.
- Missing file path — `fd`.
- Repo-wide search or code-shape matching — switch to `searching-code`.

## Progressive Disclosure Workflow

1. Confirm the scope: known file, known module, or known symbol. If the scope is
   repo-wide, switch to `searching-code`.
2. Outline first when a target file is known. `smart_outline` shows every
   function/class/interface with bodies collapsed.
3. Search symbols only after narrowing the area. `smart_search` finds likely
   definitions and nearby callers without dumping whole files.
4. Unfold targeted symbols. `smart_unfold` extracts exact function source by AST
   node and avoids truncation.
5. Read only if needed. Fall back to Read for files where AST parsing is not
   useful or exact full-file context matters.

## Key Advantages

- Complete function bodies instead of chopped line ranges.
- Symbol lists without full-file reads.
- Predictable token cost through outline → search → unfold.
- Clean handoff: use `searching-code` first for repo maps, then use this skill
  to extract the few symbols worth reading.

## Failure Handling

- claude-mem plugin unavailable: use `rg`/`fd` for bounded lookup and Read for
  targeted files; note the token cost difference.
- Scope is repo-wide or structural: switch to `searching-code` instead of
  forcing local navigation into a search job.
- `smart_outline` returns no symbols: skip to targeted Read and report the file
  type.
- `smart_search` returns too many matches: narrow the term, add a path filter,
  or switch to `searching-code` if the desired answer is repo-wide.
