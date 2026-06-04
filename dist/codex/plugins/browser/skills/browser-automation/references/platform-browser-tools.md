# Platform Browser Tools

Choose the runtime from tools visible in the active session. Prefer an exposed
browser tool over installing a new runtime.

## Claude Code

Use Claude in Chrome browser tools when they are visible in the current session.
Use them for interactive exploration, authenticated sessions, form flows,
debugging, screenshots, and rendered-state checks.

If the user wants Claude in Chrome and no browser tools are visible, tell them
to enable `claude-in-chrome` with `/mcp`.

Fallback: project runner, then `playwright-skill`.

## Codex

Use Codex app browser tools when Browser use is visible in the current session.

Codex CLI has no documented native browser tool. Fallback: project runner,
Playwright MCP when its browser tools are visible, then `playwright-skill`.

## Pi

Use browser tools if the active session exposes them. Otherwise use the project
runner, then `playwright-skill`. In ordinary Pi harnesses, prefer headless
screenshots and manifests over headed mode because the visible browser is not
usually exposed to the agent.

## Gemini

Use browser tools if the active session exposes them. Otherwise use the project
runner, then `playwright-skill`.

## Playwright Fallback

Use Playwright for repeatable scripts/tests, cross-browser checks, traces,
video, screenshot batches, or when no platform browser tool is available.

`playwright-skill` is support-only. Use it after `browser-automation` selects
the fallback; do not route user intent to it directly. Use its screenshot CLIs
before writing custom one-off batch scripts.
