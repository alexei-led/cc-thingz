# Context7 CLI Reference

Use this file only for Tier 1 docs lookup in `looking-up-docs`. Do not use it for
Context7 skill registry management.

## Workflow

1. Identify the library and version from local evidence when possible.
2. Build a specific query from the user's real topic. Avoid one-word queries.
3. If the user provided `/org/project` or `/org/project/version`, call docs
   directly with that ID.
4. Otherwise resolve the library ID first, then fetch docs:

   ```bash
   ctx7 library <name> "<specific query>"
   ctx7 docs /org/project "<specific query>"
   ```

5. Select the best library ID:
   - Prefer exact or near-exact library names.
   - Prefer a result whose description matches the user's topic.
   - Prefer version-specific IDs when the requested version appears.
   - Ask for clarification when the library name is ambiguous.
6. Ground the answer in the returned docs. Quote only relevant excerpts.
7. Report the Context7 library ID, matched version when visible, and whether
   fallback was needed.

## Missing CLI or Authentication

If `ctx7` is unavailable, replace `ctx7` with `npx ctx7@latest` or
`bunx ctx7@latest` rather than stopping:

```bash
npx ctx7@latest library <name> "<specific query>"
npx ctx7@latest docs /org/project "<specific query>"
```

If authentication or an API key is required, tell the user to configure it in
their shell or secret manager. Do not ask the user to paste secrets into chat.

## Limits and Fallback

- Do not include secrets, credentials, private payloads, personal data, or
  proprietary code in any query.
- Always pass a real query to both commands.
- Do not call `ctx7 library` more than 3 times for one user question.
- Do not call `ctx7 docs` more than 3 times for one user question.
- If docs are missing or weak, rephrase once and try one alternate library name.
- If docs remain insufficient, report Context7 exhausted and continue to
  `references/official-sources.md`.
