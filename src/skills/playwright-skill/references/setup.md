# Setup — Playwright Support Runtime

## Runtime selection

- Require Node.js 18+ and npm for fallback package installation.
- Resolve Playwright from the caller project first; keep that project's version.
- Otherwise install exactly Playwright 1.57.0 into
  `$XDG_CACHE_HOME/cc-thingz/playwright/1.57.0`, defaulting to `~/.cache`.
- Do not run dependency installs in the plugin directory.
- Package availability and browser binary availability are separate checks.

## Explicit browser setup

From the loaded skill directory, or with an absolute helper path:

```bash
node scripts/setup-runtime.js chromium
```

For other browsers:

```bash
node scripts/setup-runtime.js firefox webkit
```

A missing browser error also prints the resolved Playwright CLI installation
command. Use that command so browser binaries match the selected package version.
Setup may require network access; report installation failures explicitly.

## Verify

```bash
node scripts/screenshot-url.js \
  --url https://example.com \
  --out /tmp/playwright-example.png \
  --json
```

Check the manifest and image. Successful package import alone does not verify launch.
Chromium sandboxing stays enabled by default. `PLAYWRIGHT_SKILL_NO_SANDBOX=1` is
an explicit environment-specific opt-out, not a general setup step.
