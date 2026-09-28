---
description: Find exact, version-correct library/API/framework docs through one lookup
  workflow. Use when the user says "look up docs", "how to use", "API for", "syntax
  for", "examples of", "show me the docs", mentions "ctx7"/"Context7", passes a `/org/project`
  library ID, or needs API signatures, config keys, syntax, examples, or versioned
  docs. NOT for comparisons, current-state or release-behavior questions, best-practice
  surveys, or recent ecosystem news — use researching-web.
name: looking-up-docs
---

# Documentation Lookup

Answer API, syntax, and config questions from version-correct sources. When a
lookup tool is available, do not answer syntax from memory.

Never put secrets, credentials, personal data, private payloads, or proprietary
code into an external query. Strip them and still look up the public docs; if
the question cannot be asked without them, answer from local context and say
so.

## Lookup chain

Stop at the first tier that grounds the answer.

- Tier 0, version: find the exact package and version from manifests,
  lockfiles, or tool output. If there is none, say `version unknown` and use
  the latest stable docs. Never invent a version.
- Tier 1, Context7: follow [references/context7-cli.md](references/context7-cli.md).
  Treat Tier 1 as exhausted when Context7 is unavailable, rate-limited, returns
  the wrong version, or finds nothing after one rephrase and one alternate
  library name.
- Tier 2, official docs and registries: use
  [references/official-sources.md](references/official-sources.md). Use web
  search only to discover primary sources (the researching-web skill covers
  platform web tools), then cite the primary URL.
- Tier 3, GitHub: releases, tags, and source at the matching tag, when docs are
  missing, incomplete, or version-mismatched. Issues, PR comments, blogs, and
  generated summaries are clues, not authority.
- Tier 4, gap report: state the version needed versus found, what you tried,
  and the safest next step. Do not fabricate syntax.

If the request turns into a comparison, current-state, or release-behavior
question, hand it to researching-web and offer a docs lookup for the chosen
library afterwards.

## Response

Give the answer, not a transcript of the lookup, unless the user asks for the
process. Include:

1. Library and version, or `version unknown`.
2. The tier that produced the answer and any fallback used.
3. Syntax or example grounded in the source.
4. A source URL, Context7 library ID, or GitHub tag and path for each claim.
