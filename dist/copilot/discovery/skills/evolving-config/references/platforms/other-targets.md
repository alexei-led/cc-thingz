# Copilot, Cursor, and Grok

Read when the audit covers GitHub Copilot, Cursor, or Grok packages.

Coverage here is package layout only, taken from the Agent Bundler target
contracts. Settings, permissions, and hook policy for these targets are a gap:
check the official docs below and mark such findings as doc-sourced with lower
confidence.

- Copilot: package root holds `plugin.json`, `skills/`, `agents/`, and
  `hooks.json`; the catalog is `.github/plugin/marketplace.json`. Docs:
  `https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-plugin-reference`
- Cursor: package root holds `.cursor-plugin/plugin.json`, `skills/`, `agents/`,
  and `hooks/`; the catalog is `.cursor-plugin/marketplace.json`. Docs:
  `https://cursor.com/docs/plugins`
- Grok: uses a Claude-compatible plugin root and reads
  `.claude-plugin/marketplace.json`; validate with `grok plugin validate <root>`.
  Docs: `https://docs.x.ai/build/features/skills-plugins-marketplaces`

In cc-thingz, Copilot and Cursor ship portable artifacts without a
repo-owned runtime envelope, so role limits there are advisory. Claude and Grok
root compatibility cannot both be enabled.
