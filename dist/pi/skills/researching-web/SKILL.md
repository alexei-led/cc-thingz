---
description: Web research via platform web tools. Use for technical comparisons, current-state
  and release-behavior questions, recent facts, ecosystem news, best practices, standards,
  or questions needing grounded web evidence. NOT for exact API syntax, config keys,
  or code examples — use looking-up-docs for those. NOT for repo-specific questions
  — search local files first.
name: researching-web
---

<!-- Pi platform guidance -->
<!-- Use installed Pi tool names exactly. Installed extensions may add toolsets such as Task*, Monitor*, and Loop*; use the visible tool names exactly and do not translate them to Claude syntax. -->
<!-- Prefer Task* over `todo` when task-tracking tools are available; `todo` is the cc-thingz fallback. Prefer MonitorCreate for long-running background commands and LoopCreate for scheduled or event-driven follow-up instead of Bash sleep/poll loops. -->
<!-- Use subagent for delegated work. Use wait to block on async subagent runs only when no independent work remains. -->
<!-- Use ctx7 or npx ctx7@latest through bash when Context7 documentation lookup is required. -->

# Web Research

Use web tools for grounded external research. Prefer primary sources, official docs,
and current evidence. Do not answer from memory when the user asked for research.

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

## Conditional References

- [sources.md](references/sources.md) — read when choosing between web tools or evaluating source quality: tier ranking, stale-source detection, platform-specific tool guidance (Pi `web_search`/`web_answer`/`web_research`), source caching.

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
