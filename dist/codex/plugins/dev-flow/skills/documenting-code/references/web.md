# Web Documentation

Use this only for HTML, CSS, JavaScript, HTMX, or browser-facing docs. The host
skill owns scope, editing, and verification.

## Human-facing web docs

- Explain what the user can do, then show the shortest useful example.
- Keep setup, routes, UI states, and browser requirements current.
- Use screenshots or Mermaid only when existing docs support them and they answer
  a real layout, state, or flow question.
- Match existing visual style instead of inventing fonts, colors, or custom sections.

## Comments

Keep comments that explain:

- non-obvious event ordering
- browser quirks
- accessibility constraints
- HTMX target or trigger choices that are not self-evident
- complex regex or layout hacks

Delete comments that restate selectors, loops, obvious DOM operations, or CSS property names.

Good:

```javascript
// Sequential to avoid API rate limiting during search-as-you-type.
for (const query of queuedQueries) {
  await search(query);
}
```

## Accessibility docs

Document accessibility behavior when it is part of the user contract: keyboard
shortcuts, focus behavior, ARIA labels, announcements, and reduced-motion support.
Do not add redundant ARIA guidance when semantic HTML already explains behavior.

## Tests

Avoid comments in browser tests unless they explain timing, external browser
behavior, or why a specific accessibility edge case matters.

## Checks

Prefer configured project checks. If available, use narrow web checks:

```bash
npx html-validate .
npm run lint
npm run test
```

If a browser is needed to verify behavior, state the gap instead of guessing.
