---
{"description":"Web research via platform web tools. Use for technical comparisons, current-state and release-behavior questions, recent facts, ecosystem news, best practices, standards, or questions needing grounded web evidence. NOT for exact API syntax, config keys, or code examples — use looking-up-docs for those. NOT for repo-specific questions — search local files first.","name":"researching-web"}
---
<!-- Pi platform guidance -->
<!-- Use installed tool names. Discover callable tools before batching independent calls in codemode; model-only UI/orchestration tools must be called directly. -->
<!-- Read required skill/instruction files through direct read when exposed or through Code Mode. If an optional pruning extension is installed, verify its output protection semantics; do not assume nested-path protection. Code Mode composes calls; subagents or controllers own durable workflows. Async subagents notify natively: yield rather than poll. -->


# Web Research

Answer with current, cited evidence and keep sourced facts apart from your
recommendation. Research questions get web evidence, not answers from memory.

Never put private code, secrets, credentials, or proprietary data into a web
query; answer those from local context and say what that limits.

## Tools

Match the tool to the question with whatever web tools the runtime provides:

- Simple fact: one focused search or answer query.
- Source selection: search, then fetch the best primary sources.
- Broad investigation: a deep or asynchronous research tool when available;
  otherwise chain searches with targeted fetches and note the fallback.
- Detail on a source already found: fetch that URL instead of searching again.

Fetch enough sources to support each claim; fetch every citation only when
the risk or ambiguity justifies it. For source ranking, stale-source signals,
and Pi web tools, read [references/sources.md](references/sources.md).

## Judgment

- Prefer specifications, official docs, maintainer release notes, and primary
  announcements. Treat blogs and forum answers as supporting evidence.
- Check sourced facts against the local project's constraints before
  recommending a change.
- When sources conflict, cite both sides and lower confidence unless one is
  clearly more authoritative or current.
- Flag stale-source risk when recency matters.
- When live web access is unavailable, say so and label the answer as limited
  instead of presenting an uncited recommendation as fact.

## Platform additions

No target-specific additions.

## Output

```markdown
## Research Result

### Research Question

<question and the decision it informs>

### Answer

<concise answer>

### Evidence

- <source title/url> — <what it supports>

### Recommendation

<recommendation separated from sourced facts, or none>

### Fit For This Repo

<what changes because of local constraints>

### Unknowns and Gaps

<conflicts, stale-source risk, missing evidence, or blocked retrieval>
```
