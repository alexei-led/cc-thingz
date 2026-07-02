---
description: Simple web development with HTML, CSS, JS, and HTMX. Use when working
  with .html, .css, or .htmx files, web templates, stylesheets, or vanilla JS scripts.
  NOT for React/Vue/Angular (use writing-typescript) or Node.js backends.
name: writing-web
---

# Web Development

## Scope

- Use for HTML, CSS, HTMX, vanilla JS, and server-rendered templates.
- Do not use for React, Vue, Angular, TypeScript, Node.js backends, or app architecture.
- Follow existing template language, asset pipeline, framework, accessibility, and security conventions.
- Do not add a dependency, build step, or framework unless the project already uses it or the user approves.

## Reference Reads

- Read `references/patterns.md` before layout, behavior, accessibility, or security changes; skip for copy-only edits.

## Defaults

- Prefer semantic HTML and CSS; add HTMX or JS only when native browser behavior is insufficient.
- Use mobile-first, fluid CSS. Put repeated design tokens in custom properties; keep one-off values local.
- Preserve usable links and forms when practical.
- Treat accessibility, responsive behavior, and safe rendering as required behavior.
- Escape untrusted output; avoid `innerHTML` unless project sanitizer marks content trusted.

## Comments

- Use HTML comments only for template boundaries, generated blocks, or security assumptions that are not obvious from markup.
- Use CSS comments for non-obvious hacks, browser constraints, or integration boundaries.
- Use JS comments only for non-obvious constraints, invariants, side effects, tradeoffs, or browser quirks.
- Keep comments short. Move longer rationale to docs, issue links, or design notes.
- Do not comment obvious markup, selectors, declarations, or event handlers.
- Keep UI tests readable without comments; add one only for unobvious fixtures, browser setup, timing, or regression context.

## Verification

- Run project-configured format, lint, validation, tests, and browser checks for the changed files.
- For UI changes, check mobile and desktop widths plus keyboard navigation.
- For changed interactive behavior, run a browser test or state why it was skipped.
- If a check is unavailable, state the gap and run the closest configured gate.
- For rendered-browser verification (screenshots, live interaction, cross-viewport checks), use `browser-automation`.

## Failure Handling

- HTML or accessibility validation fails: fix the markup; do not suppress configured checks.
- HTMX request does not fire: check trigger, target, swap, response status, and CSRF/auth headers before adding JS fallback.
- Project conventions or checks are unclear: inspect config first; if still unclear, state the assumption and smallest safe gate.
- Broad, risky, or destructive change: state the risk and ask before acting. Do not run destructive commands.

## Final Response

- Files changed:
- Checks:
- Skipped checks:
- Risks/follow-ups:
