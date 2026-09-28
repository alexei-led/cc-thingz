# Platform Browser Tools

Choose the runtime from the tools visible in the current session. Prefer an
exposed browser tool over installing a new runtime. When none fits, fall back to
the project runner, then the bundled Playwright scripts.

## Claude Code

Use Claude in Chrome browser tools when they are visible, for interactive
exploration, authenticated sessions, form flows, screenshots, console logs, and
rendered-state checks. If the user wants Claude in Chrome and no browser tools
are visible, tell them to enable `claude-in-chrome` with `/mcp`.

## Codex

Use the Codex app browser tools when Browser use is visible. Codex CLI has no
native browser tool; use Playwright MCP when its tools are visible, otherwise
the fallbacks above.

## Pi

Use browser tools if the session exposes them. Pi usually does not show the
agent a visible browser, so use headless screenshots and manifests as evidence.
