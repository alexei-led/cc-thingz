# Web Review Reference

Host skill owns scope, severity, scoring, and output. This file adds HTML, CSS, JavaScript, and HTMX checks.

## Tool-enabled review

Run configured validators only when the active role can execute commands and the project already uses them.

Useful web gates:

```bash
npx html-validate <files>
npx stylelint <files>
```

Use project scripts when present. Treat tool output as evidence, then map it through the severity rubric. If validators are missing, report the gap and continue source review.

## Read-only review

When commands are unavailable, read the changed templates, scripts, and styles. For server-rendered templates, inspect enough surrounding context to identify whether data is escaped, trusted, or supplied by users.

## Focus checks

Security:

- XSS from raw HTML sinks, unsafe markdown, inline event handlers, or user data inserted without escaping.
- CSRF missing from state-changing forms or HTMX requests when server context shows the need.
- Secrets, tokens, API keys, or internal URLs in client-side code.
- Unsafe redirects or navigation from unvalidated URLs.
- Mixed-content or insecure external resource loading.

Correctness:

- Broken form names, missing required fields, invalid IDs, duplicate IDs, or mismatched labels.
- HTMX target, swap, trigger, or header mismatch that breaks the intended flow.
- Client-side code relying on elements that may not exist.

Accessibility:

- Images missing useful alt text.
- Inputs without labels or accessible names.
- Buttons or links that are not keyboard-accessible.
- Focus outline removed without a visible replacement.
- ARIA that conflicts with native semantics.

Performance:

- Blocking scripts without defer or module use where it affects page load.
- Large images without dimensions, lazy loading, or appropriate formats.
- CSS import chains or unused heavy assets in the changed path.
- Expensive DOM work on repeated events.

Tests and docs:

- Changed user-visible flow without browser, integration, or template test coverage when the project has such tests.
- User-facing text, API behavior, or accessibility behavior changed without matching docs when docs are in scope.

## Failure handling

- Server-side escaping or CSRF context missing: use Needs review and name the missing template engine, route, or middleware.
- Contrast cannot be measured: use Needs review for visually suspicious colors rather than a confirmed finding.
- Framework outside this scope: limit findings to changed HTML, CSS, JS, or HTMX behavior and report reduced coverage.
