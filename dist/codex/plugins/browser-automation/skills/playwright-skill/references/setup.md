# Setup — Playwright Support Runtime

First-time installation of Playwright and Chromium for the bundled `scripts/run.js` executor used by `browser-automation`.

## Prerequisites

- Node.js 18+ (LTS recommended)
- One of: `bun` (preferred) or `npm`

## Install

### With bun (preferred)

```bash
cd scripts && bun install && bunx playwright install chromium
```

### With npm (fallback)

```bash
cd scripts && npm install && npx playwright install chromium
```

That installs the `playwright` Node package locally and pulls the Chromium browser.

## Verify

```bash
node scripts/run.js "console.log(await chromium.launch().then(b => b.version()).then(v => (b => v)(b)))"
```

If it prints a Chromium version, setup is good.

## Auto-install fallback

If you skip explicit setup, `scripts/run.js` detects missing Playwright on first invocation and runs `bun install && bunx playwright install chromium` itself. Manual setup is faster and avoids the bun dependency on first run if you're using npm.

## Other browsers

The default install only fetches Chromium. To use Firefox or WebKit:

```bash
# bun
cd scripts && bunx playwright install firefox webkit

# npm
cd scripts && npx playwright install firefox webkit
```

Or all three at once via the `install-all-browsers` script:

```bash
cd scripts && bun run install-all-browsers   # or: npm run install-all-browsers
```
