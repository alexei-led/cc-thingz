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
node scripts/run.js "console.log(JSON.stringify(await helpers.detectDevServers()))"
```

One server → use it. Multiple → ask which. None → ask for a URL.

## Run a temporary browser script

Write scripts outside the skill directory (typically under `/tmp`), then:

```bash
node scripts/run.js /tmp/playwright-check.js
```

## Rules

- Never write generated scripts or artifacts into the skill directory or user project.
- Use `/tmp/playwright-*` for generated scripts, screenshots, traces, and logs.
- Prefer visible browser mode unless the user asks for headless.
- Parameterize target URLs.
- Return artifact paths for screenshots, traces, and logs.
- Higher-level browser workflow stays in `browser-automation`.

## Output

Report the target URL, actions run, artifact paths, and failures. Base success claims on script output or artifacts, not on command completion alone.

## Failure handling

- `run.js` not found: run from the `playwright-skill` directory.
- Dev server not detected: ask for the URL.
- Script syntax error: quote the failing line, state the cause, rewrite that section before rerunning.
- Playwright install failure: use `references/setup.md`.
