# Setup — Playwright Support Runtime

Install Playwright and Chromium for the bundled executor and screenshot helpers
used by `browser-automation`.

## Prerequisites

- Node.js 18+
- `bun` or `npm`

## Install

Run from the `playwright-skill` directory, then `cd scripts`.

### With bun

```bash
cd scripts && bun install && bunx playwright install chromium
```

### With npm

```bash
cd scripts && npm install && npx playwright install chromium
```

## Verify runner

```bash
node scripts/run.js --json "console.log(JSON.stringify({ hasChromium: !!chromium }))"
```

If it prints JSON with `hasChromium: true`, setup is good.

## Verify screenshot helper

```bash
node scripts/screenshot-url.js \
  --url https://example.com \
  --out /tmp/playwright-example.png \
  --json
```

If it prints a manifest and `/tmp/playwright-example.png` exists, screenshot
capture is good.

## Auto-install fallback

`run.js`, `screenshot-url.js`, and `screenshot-sequence.js` install Playwright
on first use when missing. They try bun first and npm second. If auto-install
fails, run one of the install commands above from the `playwright-skill`
directory.

## Other browsers

Install only when Firefox or WebKit is needed.

```bash
# bun
cd scripts && bunx playwright install firefox webkit

# npm
cd scripts && npx playwright install firefox webkit
```
