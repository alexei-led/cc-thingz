# Web patterns

## HTML

- Use meaningful landmarks.
- Use `button` for actions and `a` for navigation.
- Use `details`/`summary` for disclosure and `dialog` for modals when supported by the project.
- Preserve page heading hierarchy; avoid skipped levels in page context.
- Label every control; group related controls with `fieldset`/`legend`; use `autocomplete` when helpful.
- Prefer native validation and input types. Add ARIA only when native HTML cannot express state.

## CSS

- Prefer `gap`, logical properties, and scalable units (`rem`, `em`, `clamp`).
- Use `:focus-visible`; respect `prefers-reduced-motion` for animations.
- Avoid deep nesting, layout floats, pixel-locked pages, and `!important` except at integration boundaries.

## HTMX

- Use HTMX when the server owns the state or HTML fragment.
- Set explicit `hx-target` and `hx-swap`; return fragments shaped for that target.
- Preserve normal form `action` and `method` when practical.
- Include CSRF/auth headers through the project's existing mechanism.
- Handle loading, empty, and error states near the target.

## JavaScript

- Keep scripts small and scoped; use event delegation for dynamic content.
- Prefer module or local scope over globals.
- Use safe DOM APIs such as `textContent`, `classList`, and `dataset`.
- Clean up timers, observers, and listeners when components can be removed.
