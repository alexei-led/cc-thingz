---
allowed-tools:
- Task
- Read
- Grep
- Glob
- WebFetch
- mcp__perplexity-ask__perplexity_ask
argument-hint: <research question>
context: fork
description: Web research via platform web tools. Use for technical comparisons, current-state
  and release-behavior questions, recent facts, ecosystem news, best practices, standards,
  or questions needing grounded web evidence. NOT for exact API syntax, config keys,
  or code examples — use looking-up-docs for those. NOT for repo-specific questions
  — search local files first.
name: researching-web
user-invocable: true
---

# Web Research

Follow the base skill. This Claude overlay only defines tool use and execution details.

## Scope

Use this for:

- comparisons and trade-offs
- recent facts, current-state questions, and release behavior
- standards and external best practices
- ecosystem, licensing, or market facts
- vendor docs as evidence for non-syntax claims

Do not use this for:

- exact API syntax, config keys, or code examples → `looking-up-docs`
- repo-specific questions that local files can answer
- private code, secrets, credentials, or proprietary data

## Tool selection

Choose tools by question type:

- Simple factual question: use the platform's focused answer or search tool.
- Source selection: search first, then fetch or read the best official or primary sources.
- Broad investigation: use deep or asynchronous research when available.
- Follow-up detail on a cited source: fetch the relevant source directly.

Do not hardcode one provider as the answer for every question. Use the tool that
best matches the question and the available runtime.

## Workflow

1. Restate the research question and the decision it should inform.
2. Decide whether the question is simple, source-selection, or broad investigation.
3. Gather sources with the matching tool.
4. Prefer primary or official sources when they can answer the question.
5. Compare sourced facts against local project constraints before recommending changes.
6. Separate sourced facts from recommendation or judgment.
7. Report unknowns, stale-source risk, and gaps directly.

If the user asks for the workflow itself, describe the source-gathering plan and
output structure; do not present an uncited recommendation as fact.

## Failure handling

- No useful results: report the gap directly; do not fabricate sources.
- Live web unavailable: say so explicitly and report that the answer is limited.
- Question requires private code or credentials: refuse the web query and answer only from local context.
- Deep research unavailable: fall back to search plus focused answer queries and note the fallback.
- Sources conflict: describe the conflict, cite both sides, and avoid a confident recommendation unless one source is more authoritative or current.
- Only secondary sources found: say that primary-source confidence is limited.
- Source looks stale and recency matters: flag stale-source risk explicitly.

## Output contract

```markdown
## Research Result

### Research Question

<question and decision it informs>

### Answer

<concise answer>

### Evidence

- <source title/url> — <what it supports>

### Recommendation

<recommendation separated from sourced facts, or none>

### Fit For This Repo

<what changes because of local constraints>

### Unknowns and Stale-Source Risk

<unknowns, conflicting sources, or recency risk>

### Gaps

<any missing evidence or blocked retrieval>
```

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
