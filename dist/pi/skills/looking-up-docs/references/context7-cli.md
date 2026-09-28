# Context7 CLI

Tier 1 lookup commands. Not for Context7 skill registry management.

## Commands

If the user gave `/org/project` or `/org/project/version`, fetch docs with that
ID directly. Otherwise resolve the library first:

```bash
ctx7 library <name> "<specific query>"
ctx7 docs /org/project "<specific query>"
```

- Pass the user's real topic as the query in both commands, never a one-word
  placeholder.
- Pick the ID whose name and description match the topic; prefer a
  version-specific ID when the requested version appears. Ask when the library
  name is ambiguous.
- Quote only the relevant excerpts, and report the library ID and the matched
  version when visible.

## Missing CLI or authentication

If `ctx7` is not installed, run the same commands through `npx ctx7@latest` or
`bunx ctx7@latest`. If the CLI needs an API key, tell the user to set it in
their shell or secret manager; do not ask them to paste it into chat.

## Limits

- At most 3 `ctx7 library` calls and 3 `ctx7 docs` calls per question.
- Then report Tier 1 exhausted and continue to official sources.
