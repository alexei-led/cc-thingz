# TypeScript Refactoring Caveats

- Language-service rename follows import/export chains; it misses dynamic `import()`/`require()` with template strings, string-keyed events, action types, and serialized keys.
- Moving a file breaks relative imports and `tsconfig` `paths`/`baseUrl` aliases and project references.
- Renaming a published export breaks consumers; add a deprecated re-export. Check sibling packages in a monorepo.
- Renaming a React component changes its display name and string-based snapshots.
- Property renames change serialized JSON keys unless a schema or `toJSON` maps them.
- Barrel (`index.ts`) changes affect tree-shaking and cycles; run the project's cycle checker (madge, dependency-cruiser) when barrels change.
