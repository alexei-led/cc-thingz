# Sources and Web Tools

## Source ranking

When several sources answer the same claim, cite the highest available:

1. Specification or standards body (RFC, W3C, ECMA, ISO).
2. Official project documentation.
3. Maintainer release notes, changelogs, or blog posts.
4. Peer-reviewed paper or authoritative book.
5. Third-party guide with an explicit version and date.
6. Recent, well-voted Stack Overflow answer.
7. Other blogs, tutorials, and forum threads.

Do not cite a rank 6–7 source as definitive when a rank 1–2 source exists.

## Stale-source signals

Flag stale-source risk when:

- The source is more than 18 months old in a fast-moving ecosystem (JS, Python
  packaging, cloud APIs, LLM tooling).
- It covers a version older than the project's current dependency.
- It predates the time horizon of the question.
- The official docs deprecate an endpoint, flag, or key it relies on.

## Pi web tools

- `web_search`: multi-query search with titles, URLs, and snippets. Use
  `search_recency_filter` when freshness matters and `search_domain_filter` to
  restrict to official docs.
- `web_answer`: grounded single-turn answer. Use it for quick facts; it does
  not replace reading primary sources.
- `web_research`: asynchronous deep investigation that delivers a report. Use
  it for open-ended or multi-step questions.
