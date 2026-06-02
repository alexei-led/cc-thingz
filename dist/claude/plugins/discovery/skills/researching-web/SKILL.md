---
allowed-tools:
- Task
- Read
- Grep
- Glob
- WebFetch
- mcp__perplexity-ask__perplexity_ask
context: fork
description: Web research via Perplexity and platform web tools. Use for technical
  comparisons, recent facts, ecosystem news, best practices, standards, or questions
  needing grounded web evidence. NOT for API syntax lookup or code examples — use
  looking-up-docs for those. NOT for repo-specific questions — search local files
  first.
name: researching-web
---

# Web Research with Perplexity

**Default**: Call Perplexity MCP directly.

## Critical Routing Rules

- Use this for web-grounded research: comparisons, recommendations, best practices, standards, recent developments, licensing, ecosystem, and market/release facts.
- Do not use this for narrow API syntax or framework examples. Route those to `looking-up-docs`; prefer official docs for exact syntax.
- Do not answer research questions from memory. Use current sources, cite URLs, and mark stale-source risk or unknowns. If live retrieval is unavailable, say exactly that final evidence must be grounded in URL-cited sources before factual claims or recommendations are trusted.
- Separate sourced facts from recommendation/judgment. If evidence is missing, say what is missing instead of filling gaps.
- If the user asks to "describe the workflow", describe the source-gathering and output structure; do not present an uncited final recommendation as fact.

## Response Contract

For research output, include:

1. Research question and decision criteria.
2. Sources consulted or source plan; citations/URLs required for factual claims. If only a plan is available, state: "final evidence must be grounded in URL-cited sources."
3. Evidence table or bullets grouped by criterion.
4. Recommendation separated from sourced facts.
5. Unknowns, assumptions, and stale-source risks.

## Best For

- Technology comparisons (X vs Y)
- Best practices, industry standards
- OWASP, security guidelines
- Official docs as supporting sources for non-syntax facts
- Stable technical content

## Default Mode: Direct Web Research

Use this for 90% of research requests. When user says "ask Perplexity", "research", "look up", etc., use the available web research tool with a scoped research question.

This is fast, reliable, and what users expect.

## Query Formulation Tips

- Be specific: "Go 1.25 error handling best practices 2025"
- Include context: "Redis vs Memcached for session storage in Go services"
- Ask comparisons: "Pros and cons of gRPC vs REST for microservices"
- Include year: "Claude Code context optimization 2025"

## Reference Following (Deep Research)

After Perplexity returns results with citations:

1. **Review all cited URLs** in the response
2. **WebFetch top 2-3 most relevant sources** for deeper context
3. **Synthesize comprehensive answer** combining all sources

```
# After Perplexity response with citations
WebFetch(url="<cited-url-1>", prompt="Extract key details about <topic>")
WebFetch(url="<cited-url-2>", prompt="Extract implementation examples")
```

Use reference following when:

- Initial answer is high-level and needs specifics
- User asks "tell me more" or "dig deeper"
- Implementing something that needs detailed guidance

## Output Structure

```markdown
## Summary

[Key findings - 2-3 sentences]

## Details

[Organized findings by topic]

## Recommendations

[Actionable items for the project]

## Sources

- [Source](url) - [what was learned]
```
