# TypeScript Linting

## Tool Selection

Use the project's lint and format scripts first. Pick one formatter and one linter per file:

- Project config and package declarations decide. When several are declared, prefer Oxfmt, then Biome, for formatting, and Oxlint, then Biome, for linting.
- With no project choice, use an installed Oxfmt or Biome, else Prettier, for formatting; an installed Oxlint or Biome, else ESLint, for linting.
- Never run overlapping Biome and ESLint lint passes.

## Edit Loop

Safe fixes in file-modifying hooks, scoped to changed files:

```bash
oxfmt --write path/to/changed.ts
biome format --write path/to/changed.ts
biome lint --write path/to/changed.ts
oxlint --fix path/to/changed.ts
```

- Commit and CI checks stay non-mutating (`biome lint`, `oxlint`, `eslint`).
- Use package scripts for whole-project checks instead of widening a file-scoped command.
- Clear lint caches only when diagnosing cache corruption.
- `--quiet` skips warn-level rules; use it only for a focused hot-path error check.

## Type-Aware Lint

- It costs about as much as a TypeScript build. Keep a cheaper syntax/style path for the edit loop when many rules are type-aware.
- Point typed lint at package-level tsconfigs, not recursive globs, and keep `include` away from build output, generated files, and fixtures.
- Keep the project's typescript-eslint setup (project service or explicit projects). Ask before rewriting lint architecture for speed.

## Slow Lint

- Profile with `TIMING=1 eslint .`. The first type-aware rule looks slow because it pays TypeScript setup, so compare slow rules one at a time.
- Use `eslint --debug` only while diagnosing.
- Do not lower severity, disable rules, or ignore files to go faster. Split a hot-path command from the full gate instead.
