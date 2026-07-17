# TypeScript refactoring reference

Use for TypeScript/JavaScript behavior-preserving refactors. The host skill owns the scope-mapping workflow and output contract; this file adds language-specific mapping tools, safety gates, and caveats.

## Scope mapping

Before editing:

- Use `tsc` language services (via IDE rename or `tsserver`) for symbol renames — they follow `import`/`export` chains across the workspace.
- Use `rg` for string-based references: route strings, dynamic `require()`, `import()` with template literals, string-keyed event names, Redux action types, and serialized JSON keys.
- For file or module moves, update all relative import paths and check `tsconfig.json` `paths`, `baseUrl`, and `references` (project references).
- For exported identifier renames in public packages, check consuming packages in the monorepo.

## Verification gate

```bash
bun x tsc --noEmit
bun test
npx eslint path/to/changed/
```

Run `tsc --noEmit` before each batch to catch type errors. Run the full test suite before final output.

## Key caveats

- Renaming an exported identifier is a breaking API change for external consumers; add a deprecated re-export alias when the package is published.
- Moving a file changes its import path; update all relative `import` statements and check `tsconfig.json` `paths` aliases that map to the old location.
- Renaming a React component changes its display name in DevTools and any string-based snapshot tests; update snapshots after the rename.
- Class or interface property renames break serialized JSON keys unless an explicit `toJSON`/`fromJSON` or schema decorator maps the old name.
- Barrel (`index.ts`) file changes affect tree-shaking and circular dependency detection; run `madge` or `dependency-cruiser` when barrel patterns change significantly.
