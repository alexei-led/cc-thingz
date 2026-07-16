# Source Selection and Tool Guidance

Read when choosing between available web tools or evaluating retrieved sources.

## Source quality tiers

Rank sources in this order when multiple candidates exist:

1. Official specification or standards body (RFC, W3C, ECMA, ISO)
2. Official project documentation (docs.project.org, official README)
3. Official vendor blog post or release notes from the project maintainers
4. Peer-reviewed paper or authoritative book
5. Well-maintained third-party guide with explicit version and date
6. Stack Overflow accepted answer with high vote count and recent activity
7. Secondary blog post, tutorial, or forum thread

Never cite a tier-6/7 source as definitive when a tier-1/2 source exists.
Prefer citing the primary source directly even if a secondary source is
easier to summarise.

## Stale-source detection

Flag stale-source risk when any of these are true:

- Publication date is more than 18 months ago for a fast-moving ecosystem
  (JS, Python packaging, cloud APIs, LLM tooling).
- The source explicitly covers a version that predates the project's current
  dependency version.
- The source is an official changelog or release notes that predates the
  question's time horizon.
- API endpoints, CLI flags, or config keys mentioned in the source have
  known deprecation notices in the official docs.

When stale-source risk applies, say so explicitly in the "Unknowns and
Stale-Source Risk" section; do not silently omit the source.

## Platform tool selection

Choose the tool that matches the question shape and what is available at
runtime. Do not hardcode one provider.

### Question types and tool fit

- Single factual question with a likely authoritative answer: use a focused
  search or direct-answer tool (e.g. `web_answer`, `WebSearch`).
- Comparison across multiple options: search for each option separately or
  use a single multi-topic search; prefer a source for each option.
- Deep investigation or synthesis across many sources: use an asynchronous
  or deep-research tool when available (e.g. `web_research` with
  `sonar-deep-research`); otherwise chain search + targeted fetch.
- Follow-up detail on a specific source already in context: fetch that URL
  directly rather than re-searching.

### Pi-specific tools

- `web_search` — fast multi-query; returns titles, URLs, snippets. Good for
  source discovery. Use `search_recency_filter` when freshness matters;
  use `search_domain_filter` when restricting to official docs.
- `web_answer` — grounded single-turn answer via Perplexity. Good for
  quick factual questions. Not a substitute for reading primary sources.
- `web_research` — async deep investigation. Fires in background and
  delivers a report. Use for open-ended or multi-step questions.
- `ctx_fetch_and_index` — fetch and index a URL for later search. Use when
  you need to read a specific doc page and query it repeatedly.

### Source caching

If the same primary source is needed for multiple sub-questions in one
session, fetch and index it once (`ctx_fetch_and_index`) and query via
`ctx_search` for subsequent lookups. Avoid re-fetching the same URL.
