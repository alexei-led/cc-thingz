# Playwright Helper for Pi

Support-only Playwright runtime/reference for `browser-automation` on Pi: dev-server detection, a script runner, and helper utilities. Do not route user intent here directly; use `browser-automation` for exploration, validation, screenshots, and browser tests.

## Path resolution

```text
~/.pi/agent/skills/playwright-skill
```

## Setup

See [`references/setup.md`](references/setup.md). First invocation of `run.js` auto-installs Playwright via bun if missing.

## Detect dev servers

```bash
node -e "require('scripts/lib/helpers').detectDevServers().then(s => console.log(JSON.stringify(s)))"
```

If multiple servers are found, ask the user which to test.

## Run a temporary browser script

Write scripts outside the skill directory (typically under `/tmp`), then:

```bash
node scripts/run.js /tmp/playwright-check.js
```

## Rules

- Never write generated tests into the skill directory.
- Prefer visible browser mode unless the user asks for headless.
- Parameterize target URLs.
- Return artifact paths for screenshots, traces, and logs.
- Higher-level browser workflow stays in `browser-automation`.
