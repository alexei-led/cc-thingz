# React TypeScript Patterns

Use for `.tsx`, hooks, component state, forms, performance, and React-specific tests. Apply project conventions first.

## Components and Props

- Use plain function components. Do not default to `React.FC`.
- Use interfaces for props when project style allows extension.
- Type `children` explicitly as `ReactNode` or the project equivalent.
- Keep components focused on rendering and user interaction. Move parsing, I/O, and domain logic out.
- Put event and callback types on props when they are part of the public component contract.

## State

- Model exclusive UI states with discriminated unions; use `patterns.md` for the shape.
- Use reducers when transitions matter, not for simple local toggles.
- Keep derived state derived during render unless caching is needed.

## Effects and Data Loading

- Prefer framework or project data-loading patterns when present.
- In effects, handle cleanup and cancellation.
- Validate loaded data in the fetcher, not inside rendering code.
- Avoid stale updates after unmount or dependency changes.
- Keep dependency arrays complete; fix stale closures instead of suppressing lint rules.

## Context

- Use context for cross-cutting dependencies or state, not as a default global store.
- Keep context values small and stable.
- Throw from custom hooks when a required provider is missing.
- Split read/write or domain contexts only when re-renders or ownership justify it.

## Forms

- Use controlled inputs or native form APIs for simple forms.
- Use the project's existing form/schema library when form state, validation, or reuse is complex.
- Validate submitted values at the boundary before producing domain types.
- Keep server/API validation errors distinct from client validation errors.

## Performance

- Do not add `memo`, `useMemo`, or `useCallback` by default.
- Memoize only for measured expensive work, stable identity required by memoized children, or dependency churn that causes real re-renders.
- Use lazy loading at route or heavy-feature boundaries, not for tiny components.

## Tests

- Read `testing.md` before changing React tests.
