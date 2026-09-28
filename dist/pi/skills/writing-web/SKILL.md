---
{"description":"Simple web development with HTML, CSS, JS, and HTMX. Use when working with .html, .css, or .htmx files, web templates, stylesheets, or vanilla JS scripts. NOT for React/Vue/Angular (use writing-typescript) or Node.js backends.","name":"writing-web"}
---
<!-- Pi platform guidance -->
<!-- Use installed Pi tool names exactly. Installed extensions may add toolsets such as Task*, Monitor*, and Loop*; use the visible tool names exactly and do not translate them to Claude syntax. -->
<!-- Prefer Task* over `todo` when task-tracking tools are available; `todo` is the cc-thingz fallback. Prefer MonitorCreate for long-running or background commands and LoopCreate for scheduled or event-driven follow-up instead of Bash sleep/poll loops. -->
<!-- Use subagent for authorized delegation. Ordinary async subagents notify the parent natively; yield instead of polling or calling bg_wait merely because a child is active. Use blocking bg_wait only for provider, detached, or other background work without a native notification when a required same-turn result is needed. -->
<!-- Current pi-subagents uses one model per launch; do not configure fallbackModels. A different model requires an explicit new launch after inspecting the failed run and partial work. Use the owning workflow/controller for retries. -->
<!-- Use ctx7 or npx ctx7@latest through bash when Context7 documentation lookup is required. -->


# Web Development

Follow the existing template language, asset pipeline, and conventions. Add a dependency, build step, or framework only when the project already uses it or the user approves; requests that need a SPA framework belong to writing-typescript.

## HTML and CSS

- Semantic HTML first; HTMX or JS only where native behavior falls short. `button` for actions, `a` for navigation, `details`/`summary` and `dialog` before custom widgets.
- Label every control; group with `fieldset`/`legend`; use native input types, validation, and `autocomplete`. Add ARIA only when HTML cannot express the state.
- Mobile-first, fluid CSS: `gap`, logical properties, `rem`/`clamp`. Design tokens in custom properties; one-off values stay local.
- `:focus-visible` styles, and animations respect `prefers-reduced-motion`. `!important` only at integration boundaries.

## HTMX

- Use HTMX when the server owns the state or the fragment. Set explicit `hx-target` and `hx-swap`, and return fragments shaped for that target.
- Keep the form's `action` and `method` so it still works without JS.
- Send CSRF and auth headers through the project's existing mechanism.
- Request not firing: check trigger, target, swap, response status, and CSRF/auth headers before adding a JS fallback.

## JavaScript

- Small scoped modules, event delegation for dynamic content, no new globals.
- Render untrusted data with `textContent`, never `innerHTML`, unless the project sanitizer marks it trusted.
- Clean up timers, observers, and listeners on elements that can be swapped out.

## Checks

UI changes need a look at mobile and desktop widths and keyboard navigation. Use browser-automation for rendered checks, screenshots, and interaction tests.

Done when the relevant build/test/lint checks pass on what you changed, or you name each check that did not run and why.
