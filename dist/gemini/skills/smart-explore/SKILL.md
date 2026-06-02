---
description: Token-efficient local code navigation and extraction. Use when exploring
  a known file or bounded module outline, finding a known symbol in a scoped area,
  or extracting exact function/type bodies with available structure tools and text-search
  fallbacks. NOT for repo-wide structural pattern search, architecture or trace-flow
  questions, ast-grep/codegraph/GitNexus evidence, or broad caller/implementation
  maps.
name: smart-explore
---

# Smart Explore: Local Code Navigation

Use cheap structure before reading large files. The goal is precise outline and
extraction from a known area, not repo-wide search.

## Boundary

Use this skill for:

- known-file outlines
- known-module outlines
- targeted symbol lookup in a bounded scope
- exact function, class, method, or type extraction
- read-next ranges after another search/review tool narrowed the area

Do not use this skill for:

- repo-wide structural pattern search
- ast-grep rule authoring or code-shape queries
- architecture, semantic flow, or "how does X work?" questions
- broad "find all implementations/callers in the repo" requests
- codegraph, GitNexus, dependency, churn, or blast-radius evidence

For those, use a dedicated repo-wide search or architecture-analysis workflow.
Return to smart-explore only after the scope is a known file, module, or symbol.

## Tool Order

1. Structure-aware outline tools for known files or modules, when available.
2. Structure-aware symbol search for a known symbol or concept in a bounded scope, when available.
3. Structure-aware unfold/extraction for exact function/type source, when available.
4. `rg` for exact text fallback when structure tools are unavailable.
5. `fd` for candidate file discovery when the file path is missing.
6. Read full files only when smaller structural views are insufficient.

## When to Use Which

- File structure at a glance — outline tool when available.
- Bounded symbol discovery — symbol search in the narrowed scope.
- Specific function/type body — targeted structure extraction when available.
- Simple string fallback — `rg`.
- Missing file path — `fd`.
- Repo-wide maps, code-shape matching, callers/callees, or architecture evidence —
  switch to a dedicated repo-wide workflow.

## Progressive Disclosure Workflow

1. Confirm the scope: known file, known module, or known symbol. If the scope is
   repo-wide, stop and use a dedicated repo-wide workflow.
2. Outline first when a target file is known. Prefer tools that show symbols
   with bodies collapsed.
3. Search symbols only after narrowing the area. Prefer tools that find likely
   definitions and nearby callers without dumping whole files.
4. Extract targeted symbols with structure-aware tools when available; otherwise
   read the smallest useful range or file.
5. Read only if needed. Fall back to Read for files where AST parsing is not
   useful or exact full-file context matters.

## Key Advantages

- Complete function bodies instead of chopped line ranges.
- Symbol lists without full-file reads.
- Predictable token cost through outline → search → unfold.
- Clean handoff from repo-wide search: extract only the few symbols worth reading.

## Failure Handling

- Structure tools unavailable: use `rg`/`fd` for bounded lookup and Read for
  targeted files; note the token cost difference.
- Scope is repo-wide, structural, architectural, graph-shaped, or historical:
  switch to a dedicated repo-wide workflow instead of forcing local navigation
  into a search job.
- Outline returns no symbols: skip to targeted Read and report the file type.
- Symbol search returns too many matches: narrow the term, add a path filter, or
  switch to a dedicated repo-wide workflow if the desired answer is repo-wide.
