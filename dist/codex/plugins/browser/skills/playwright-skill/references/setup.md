# Setup — Playwright Support Runtime

Install Playwright and Chromium for the bundled `scripts/run.js` executor used by `browser-automation`.

## Prerequisites

- Node.js 18+
- `bun` or `npm`

## Install

Run from the `playwright-skill` directory.

### With bun

```bash
cd scripts && bun install && bunx playwright install chromium
```

### With npm

```bash
cd scripts && npm install && npx playwright install chromium
```

## Verify

```bash
node scripts/run.js "const browser = await chromium.launch({ headless: true }); console.log(await browser.version()); await browser.close();"
```

If it prints a Chromium version, setup is good.

## Auto-install fallback

`run.js` installs Playwright on first use when missing. If auto-install fails, run one of the install commands above from the `playwright-skill` directory.

## Other browsers

Install only when Firefox or WebKit is needed.

```bash
# bun
cd scripts && bunx playwright install firefox webkit

# npm
cd scripts && npx playwright install firefox webkit
```
