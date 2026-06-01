---
description: Idiomatic TypeScript development. Use when writing TypeScript code, Node.js
  services, React apps, or TS design advice. Emphasizes strict typing, boundary validation,
  composition, behavior tests, and project-configured tooling. NOT for Go, Python,
  plain HTML/CSS/JS, or server-rendered templates.
name: writing-typescript
---

# TypeScript Development

## Scope

- Use for `.ts` and `.tsx`, Node.js services, React apps, typed APIs, and TypeScript design advice.
- Do not use for Go, Python, plain HTML/CSS/JS, or server-rendered templates.
- Follow the repository's TypeScript version, tsconfig, package manager, framework, test runner, and lint rules.
- Do not add dependencies or switch frameworks unless the project already uses them or the user approves.

## Required Reads

- Read `references/principles.md` before editing, generating, or reviewing TypeScript.
- Read `references/patterns.md` for data modeling, validation, async flow, and module boundaries.
- Read `references/react.md` for React components, hooks, state, forms, and performance.
- Read `references/testing.md` before adding or changing TypeScript tests.

## Defaults

- Preserve strict typing. If creating config, enable `strict`, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`, `useUnknownInCatchVariables`, `noImplicitOverride`, `noImplicitReturns`, and `noFallthroughCasesInSwitch`.
- Use `unknown` for untrusted input. Avoid `any`; isolate it only for unavoidable interop.
- Validate API, JSON, env, storage, and form data at the boundary before typed use.
- Use discriminated unions for variants, async state, and domain states.
- Use guard clauses and focused helpers. Avoid deep nesting, global state, and mixed concerns.
- Model recoverable errors explicitly with unions or `Result`. Throw Error subclasses only at boundaries where the project already does.
- Prefer composition and dependency injection over inheritance, singletons, and hidden module state.
- Avoid unsafe casts, non-null assertions, broad index signatures, boolean-flag state, and new app enums where literal unions fit.

## Testing and Verification

- For behavior changes, include success and failure tests. For React, cover loading, success, error, validation, and user interaction states when affected.
- Run the project's configured typecheck, tests, lint, and format checks for the changed package or workspace.
- Report checks run, failures, and unchecked risks. Do not claim success without a clean check or an explicit reason it was skipped.

## Failure Handling

- If project root is unclear, identify the nearest `package.json` and `tsconfig.json`; in monorepos, state the selected package.
- If strict compiler options are absent, do not silently weaken new code. State the gap and keep the change locally type-safe.
- If validation needs a schema/form library not already used, ask before adding it; otherwise use a narrow type guard.
- If typecheck or tests fail, quote the failing line, state the cause, and fix the type/model boundary before widening types.
- Do not run destructive shell commands. For broad or risky changes, state the risk and ask before acting.
