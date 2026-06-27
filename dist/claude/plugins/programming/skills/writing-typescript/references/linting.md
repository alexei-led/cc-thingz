# TypeScript Linting

Use before changing TypeScript or JavaScript lint commands, ESLint config, or
lint-heavy verification flow.

## Fast feedback

- Use the project lint command and package manager first.
- Prefer linting the changed file, package, or workspace when the command
  supports it.
- Enable and preserve ESLint cache when the project supports it:

```bash
eslint "src/**/*.{js,ts,tsx}" --cache --cache-strategy content
```

- Do not clear lint caches as a routine fix. Clear only when diagnosing cache
  corruption.
- Keep coverage, test runners, and type-aware full-project lint separate unless
  the project intentionally combines them.

## Type-aware linting

- Expect type-aware lint to cost roughly as much as a TypeScript build.
- Keep a cheaper syntax/style lint path for the edit loop when the project has
  many type-aware rules.
- Avoid wide TypeScript config globs for typed lint. Prefer package-level config
  paths over recursive all-directory globs.
- Keep TypeScript config `include` targeted so lint does not pre-parse build
  output, generated files, fixtures, or dependencies.
- Use project service when the project already uses current typescript-eslint
  patterns. Do not rewrite lint architecture only for speed without approval.

## Profiling slow lint

- Use ESLint rule timing when lint is much slower than expected:

```bash
TIMING=1 eslint .
```

- For type-aware lint, the first type-aware rule can look slow because it pays
  TypeScript cache setup. Compare slow rules one at a time before disabling one.
- Use `eslint --debug` or typescript-eslint debug output only while diagnosing;
  keep debug output off the hot path.

## Output discipline

- Use `--quiet` only for a focused hot-path error check. It skips warn-level rule
  execution unless combined with warning thresholds.
- Do not lower severity, disable rules, or ignore files just to make lint faster.
  Split slow checks into a full gate or fix the bottleneck.
- Keep generated, build, coverage, fixture, and vendor folders ignored through
  normal project ignore config.
