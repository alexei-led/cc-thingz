---
description: Web research via Perplexity and platform web tools. Use for technical
  comparisons, recent facts, ecosystem news, best practices, standards, or questions
  needing grounded web evidence. NOT for API syntax lookup or code examples — use
  looking-up-docs for those. NOT for repo-specific questions — search local files
  first.
name: researching-web
---

# Web Research

Use the runtime's available web-retrieval tools for grounded external research.
Prefer primary sources and current vendor docs.

## Platform tool selection

- Simple factual question: use the platform's focused answer or search tool.
- Source selection: search the web, then fetch or read the best official or primary sources when supported.
- Broad investigation: use the platform's deep or asynchronous research tool when available.

## Boundaries

Use this for:

- comparisons and trade-offs
- recent facts and release behavior
- standards and external best practices
- vendor docs or public evidence

Do not use web tools for private code, secrets, credentials, proprietary data,
or local code exploration. Use local search first for repo-specific questions.

## Workflow

1. Restate the research question and decide if it is simple or broad.
2. For simple factual questions, use a focused answer query.
3. For source selection, search first, then cite the best official or primary
   sources from the returned results.
4. For broad investigations, use deep or asynchronous research when available;
   tell the user when the final report will arrive later.
5. Compare claims against local project constraints before recommending changes.
6. Report uncertainty and source gaps directly.

## Failure Cases

- Web tools return no useful results: report the gap directly in the Gaps section; do not fabricate sources.
- Question requires private code or credentials to answer: refuse the web query, answer from local context only, and note the limitation.
- Deep research is unavailable: fall back to search plus focused answer queries and note the fallback.

## Output Contract

```markdown
## Research Result

### Answer

<concise answer>

### Evidence

- <source title/url or grounded result> — <why it matters>

### Fit For This Repo

<what changes because of local constraints>

### Gaps

<any missing evidence>
```
