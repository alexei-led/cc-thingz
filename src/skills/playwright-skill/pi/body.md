# Playwright Helper for Pi

Support-only Playwright runtime/reference for `browser-automation` on Pi:
dev-server detection, a script runner, screenshot helpers, and helper utilities.
Do not route user intent here directly; use `browser-automation` for
exploration, validation, screenshots, and browser tests.

## Path resolution

Run from the directory containing this `SKILL.md`. In Pi, the loaded skill path
may be under a package cache or git checkout such as `dist/pi/skills`, not a
fixed `~/.pi/agent/skills/playwright-skill` path.

## Setup

See [`references/setup.md`](references/setup.md). First invocation of `run.js`
or the screenshot helpers auto-installs Playwright via bun, with npm fallback.

## Detect dev servers

```bash
node scripts/run.js --json "console.log(JSON.stringify(await helpers.detectDevServers()))"
```

One server → use it. Multiple → ask which. None → ask for a URL.

## Run a temporary browser script

Write scripts outside the skill directory (typically under `/tmp`), then:

```bash
node scripts/run.js --quiet /tmp/playwright-check.js
```

`run.js` preserves the caller working directory, exposes Playwright globals even
when the script uses `require("fs")` or `require("path")`, and keeps runner logs
on stderr so JSON stdout stays clean.

## Screenshot helpers

Single URL:

```bash
node scripts/screenshot-url.js \
  --url http://localhost:3030/1?clicks=20 \
  --selector .slidev-page \
  --out /tmp/playwright-slide-01.png \
  --json
```

Sequence:

```bash
node scripts/screenshot-sequence.js \
  --url-template 'http://localhost:3030/{n}?clicks=20' \
  --from 1 \
  --to 17 \
  --selector .slidev-page \
  --out-dir /tmp/playwright-slidev \
  --json
```

The sequence manifest includes title, URL, screenshot path, console errors,
network failures, and HTTP responses with status >=400.

## Rules

- Never write generated scripts or artifacts into the skill directory or user
  project.
- Use `/tmp/playwright-*` for generated scripts, screenshots, traces, and logs.
- Prefer headless screenshots in Pi unless a visible browser is actually
  exposed by the platform.
- Parameterize target URLs.
- Return artifact paths for screenshots, traces, manifests, and logs.
- For SPAs, wait on rendered state with `helpers.waitForStablePage(page, { selector, animationFrames })`.
- Higher-level browser workflow stays in `browser-automation`.

## Output

Report the target URL, actions run, artifact paths, and failures. Base success
claims on script output or artifacts, not on command completion alone.

## Failure handling

- `run.js` not found: run from the directory containing this `SKILL.md`, or use
  the absolute loaded skill path.
- Dev server not detected: ask for the URL.
- Script syntax error: quote the failing line, state the cause, rewrite that
  section before rerunning.
- Playwright install failure: use `references/setup.md`.
