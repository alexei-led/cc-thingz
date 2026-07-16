# TypeScript fix reference

Use for TypeScript/JavaScript defect fixes. The host skill owns the full fix workflow; this file adds language-specific repro commands and key failure patterns.

## Repro and narrow loop

Find the fastest reliable failing signal first:

```bash
bun test path/to/file.test.ts
npx vitest run path/to/file.test.ts
npx jest path/to/file.test.ts
bun x tsc --noEmit
```

Use the narrowest test file or pattern filter while editing. Run `bun test` or `npm test` (project gate) before final output. Use the project's package manager and test runner rather than forcing a particular tool.

## Key failure patterns

- Floating promise: `async` function called without `await`, silently dropping its rejection.
- Type assertion `as T` trusting external or unknown data; validate at the boundary with a schema or runtime check.
- `undefined` dereference from optional chaining omitted (`foo.bar` instead of `foo?.bar`).
- React stale closure in `useEffect` with missing dependency, reading old state or props.
- `Promise.all` swallowing individual rejections when one settlement affects others; check settlement order and error handling.
- Dynamic `require` or `import()` with user-controlled path enabling path traversal.

## Verification

Before claiming fixed:

- Failing test or repro no longer fails.
- `tsc --noEmit` exits clean.
- ESLint and project lint script exit clean on changed files.
- No new unhandled promise rejection warnings at runtime.
