# Web Review Focus

Use writing-web for validators and project scripts.

- Escaping: for server-rendered templates, read enough context to tell trusted from user data. Raw sinks, unsafe markdown, and inline handlers are XSS paths.
- CSRF on state-changing forms and HTMX requests when server context shows the need; if the middleware or template engine is unseen, use Needs review.
- HTMX `hx-target`, `hx-swap`, `hx-trigger`, or header mismatches that break the flow.
- Duplicate or mismatched IDs, labels, and form names.
- Accessibility: accessible names, keyboard reachability, focus outline removed without replacement, ARIA fighting native semantics. Unmeasurable contrast goes to Needs review.
- Blocking scripts, unsized or unlazy images, heavy DOM work on repeated events.
