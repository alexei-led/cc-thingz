---
{"allowed-tools":["Task","Read","Grep","Glob","WebFetch","mcp__perplexity-ask__perplexity_ask"],"argument-hint":"\u003cresearch question\u003e","context":"fork","description":"Web research via platform web tools. Use for technical comparisons, current-state and release-behavior questions, recent facts, ecosystem news, best practices, standards, or questions needing grounded web evidence. NOT for exact API syntax, config keys, or code examples — use looking-up-docs for those. NOT for repo-specific questions — search local files first.","name":"researching-web","user-invocable":true}
---
# Web Research

Follow the base skill. This Claude overlay only defines tool use and execution details.

## Claude tool rules

- Use Perplexity for broad research questions, comparisons, or source discovery when it is available.
- Use `WebFetch` to inspect primary or official sources directly after source discovery.
- Do not answer research questions from memory.
- Do not route exact API syntax or code-example questions here; use `looking-up-docs`.
- Do not route repo-specific questions here when local files can answer them.

## Tool selection on Claude

- Simple factual question: use the smallest web query that can answer it.
- Source selection: use Perplexity or another available search-capable tool, then fetch the best sources.
- Broad investigation: use Perplexity first when it fits; if the runtime offers a deeper research mode, use it when the question truly needs it.
- Follow-up detail: fetch only the sources needed to support the claim.

Inspect enough sources to support the answer. Do not fetch every citation unless the
risk or ambiguity justifies it.

## Source handling

- Prefer official docs, standards, vendor docs, maintainer posts, and primary announcements.
- Treat forum summaries and secondary blogs as supporting evidence, not sole authority, when stronger sources should exist.
- If sources conflict, show the conflict and reduce confidence.
- If only a research plan is possible, say that final evidence must be grounded in URL-cited sources.

## Optional delegation

Use `Task` only for broad background research that can run independently without
changing the output contract. Keep the prompt bounded and ask it to return cited
facts, not final recommendations.

## Output

Use the base skill's `Research Result` output contract exactly.
