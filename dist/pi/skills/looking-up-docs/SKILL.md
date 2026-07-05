---
description: Find exact, version-correct library/API/framework docs through one lookup
  workflow. Use when the user says "look up docs", "how to use", "API for", "syntax
  for", "examples of", "show me the docs", mentions "ctx7"/"Context7", passes a `/org/project`
  library ID, or needs API signatures, config keys, syntax, examples, or versioned
  docs. NOT for comparisons, current-state or release-behavior questions, best-practice
  surveys, or recent ecosystem news — use researching-web.
name: looking-up-docs
---

<!-- Pi platform guidance -->
<!-- Use installed Pi tool names exactly. Installed extensions may add toolsets such as Task*, Monitor*, and Loop*; use the visible tool names exactly and do not translate them to Claude syntax. -->
<!-- Prefer Task* over `todo` when task-tracking tools are available; `todo` is the cc-thingz fallback. Prefer MonitorCreate for long-running background commands and LoopCreate for scheduled or event-driven follow-up instead of Bash sleep/poll loops. -->
<!-- Use subagent for delegated work. Use wait to block on async subagent runs only when no independent work remains. -->
<!-- Use ctx7 or npx ctx7@latest through bash when Context7 documentation lookup is required. -->

# Documentation Lookup

Get grounded, version-correct docs for a library, framework, CLI, or API.
Never answer syntax or API questions from memory when lookup tools are available.

## Scope

Use this skill for:

- API signatures, options, config keys, syntax, and examples.
- Versioned API behavior of a known library, framework, language, CLI, or
  standard library when the question is how to call or configure it.
- Context7 docs lookup, including explicit `ctx7`, `Context7`, or `/org/project`
  library-ID requests.
- Confirming versioned API behavior before writing code against an external API.

Do not use this skill for:

- Comparisons, recommendations, market research, current-state questions,
  release-behavior questions, or best-practice surveys; route to `researching-web`.
- Repo-specific questions; search local files first.
- External queries containing secrets, credentials, personal data, private
  payloads, or proprietary code.

## Reference Files

Read only what the question needs:

- `references/context7-cli.md` — Context7 lookup commands, selection rules,
  limits, and fallbacks.
- `references/official-sources.md` — primary docs and registries by ecosystem.
- `references/web-tools.md` — platform web tools, query templates, and source
  quality rules.

## Lookup Chain

Run tiers in order. Stop at the first tier that yields a grounded answer. State
which tier produced the answer and whether fallback was used.

### Tier 0 — Identify Package and Version

Find the exact package, module, CLI, language version, or framework version from
local evidence.

If no local version is available, state `version unknown` and prefer latest
stable official docs. Do not invent a version.

### Tier 1 — Context7

Use `references/context7-cli.md` for Context7 library resolution and docs fetch.
Best fit: versioned library and framework docs.

Escalate when Context7 is unavailable, rate-limited, returns no useful match
after one rephrase and one alternate library name, or returns docs for the wrong
version.

### Tier 2 — Official Docs and Registries

Use `references/official-sources.md` for language standard libraries, package
registries, and canonical project docs. Prefer primary docs or registry-linked
docs for the exact version.

Use web tools only for source discovery. Ground final syntax in URL-cited primary
sources.

### Tier 3 — GitHub Releases, Tags, and Source

Use GitHub only when primary docs or registry links are missing, incomplete, or
version-mismatched. Follow `references/official-sources.md` fallback rules.

Do not treat random issues, PR comments, blogs, or generated summaries as
authoritative API docs. Use them only as clues to primary sources.

### Tier 4 — Source Discovery or Gap Report

Use broad web research only to find primary docs after focused lookup fails. If
the question becomes a comparison, trade-off, current-state, or release-behavior
task, stop and route to `researching-web`. If no grounded source exists, report
the gap, the version needed vs found, and the safest next step.

## Limits and Failure Handling

- Never send secrets, credentials, private payloads, personal data, or
  proprietary code to any external tier.
- Always use a real, specific query; never use a one-word placeholder.
- Do not loop a tier indefinitely: one rephrase and one alternate name per tier,
  then escalate.
- If docs are version-mismatched, state the mismatch and escalate to exact-version
  registry docs, release notes, or matching GitHub tag/source.
- If all tiers fail, report the gap and do not fabricate syntax.
- If external lookup would expose private data, refuse the external query and
  answer from local context only, noting the limitation.

## Response Contract

Return a concise answer, not a workflow transcript, unless the user asks for the
lookup process.

Include:

1. Library/framework/API and version, or `version unknown`.
2. Tier that produced the answer, and fallback used if any.
3. Syntax or example guidance grounded in the source.
4. Source URL, Context7 library ID, or GitHub tag/source path for each claim.
5. Boundary note when the request is actually comparison, current-state,
   release-behavior, or broad research.

If the user asks to describe the workflow, describe the tiers and escalation
rules instead of answering from memory.
