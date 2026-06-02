# Web and Perplexity Tool Reference

Use this only for source discovery after identifying the package and version.
Use only the section for the current platform. Final syntax claims must cite
primary docs, registry pages, release notes, or source at a matching tag.

## Claude

```text
mcp__perplexity-ask__perplexity_ask  focused URL-cited source discovery
WebSearch                             find official docs
WebFetch                              read selected source
Bash(ctx7 *)                          Context7 CLI
Bash(npx ctx7@latest *)               Context7 package-runner fallback
Bash(bunx ctx7@latest *)              Context7 package-runner fallback
```

## Codex

```text
Perplexity MCP       focused URL-cited source discovery when configured
built-in web search  official-source discovery when enabled
shell                Context7 CLI when allowed
```

## Gemini

```text
Perplexity MCP     focused URL-cited source discovery when configured
google_web_search  find official docs
web_fetch          read selected source
shell              Context7 CLI when allowed
```

## Pi

```text
web_answer    quick focused factual docs questions
web_search    official-source discovery and grouped query results
web_research  broad or multi-step investigation after focused lookup fails
bash          Context7 CLI and package-runner fallbacks
```

Use source-discovery tools when source choice matters. Use quick-answer tools
only when they return enough primary-source evidence for the claim.

## Query Templates

Use focused, version-qualified queries that name the package, version, symbol
or behavior, and preferred official source:

```text
<package> <version> <symbol or option> official docs
<package> <version> migration guide <behavior>
site:<primary-domain> <package or module> <version> <symbol>
```

Avoid:

- One-word queries such as `hooks`, `auth`, or `errors`.
- Queries containing secrets, credentials, personal data, proprietary payloads,
  or private code.
- Blog-first searches when official docs can answer the question.

## Source Quality

Prefer exact-version primary sources: official docs, registries, release notes,
changelogs, or source at a matching tag.

Reject or label as weak:

- Blogs, tutorials, Stack Overflow answers, random issue comments, and generated
  summaries without primary-source confirmation.
- Latest-docs pages or repository `main` docs when the installed version is a
  released tag.
