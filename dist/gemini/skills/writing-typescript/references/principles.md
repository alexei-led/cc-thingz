# TypeScript Principles

Read this before TypeScript work. Apply project conventions first, but do not weaken type safety to fit unsafe code without approval.

## Strictness

- Treat compiler errors as design feedback, not noise to bypass.
- Keep or add strict options when creating config: `strict`, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`, `useUnknownInCatchVariables`, `noImplicitOverride`, `noImplicitReturns`, `noFallthroughCasesInSwitch`.
- Avoid `any`. Use `unknown` at boundaries and narrow before use.
- Avoid `as`, `!`, and broad index signatures unless a runtime check or external type gap justifies them.
- Prefer `satisfies` and `as const` for narrow literal data.

## Types and Data Models

- Use interfaces for public, extensible object contracts when that matches project style.
- Use type aliases for unions, mapped types, utility types, and closed variants.
- Use discriminated unions for domain states, async states, and variants.
- Use exhaustive switches with a `never` check for closed unions.
- Prefer named domain values over repeated string and number literals.

## Boundaries

- Validate untrusted data before typed use: HTTP responses, request bodies, local storage, env vars, CLI args, form data, and third-party SDK output.
- Use the project's existing schema library when present. Otherwise write small type guards.
- Keep parsing and validation close to I/O. Return typed domain data from the boundary.
- Do not return `await response.json()` as a trusted type without validation.

## Control Flow and Errors

- Use guard clauses and early returns to keep happy paths flat.
- Keep functions focused; split mixed parsing, I/O, domain logic, and rendering.
- Use `Result` or discriminated unions for recoverable domain and I/O failures.
- Throw typed/custom errors at process, framework, or API boundaries when that matches the codebase.
- Preserve cancellation, timeouts, and cleanup for async work that can outlive the caller.

## Dependencies

- Prefer standard TypeScript, platform APIs, and existing project utilities.
- Add schema, form, query, state, or test libraries only when existing project use or real complexity justifies them.
- Do not introduce a library just to avoid writing a narrow helper.

## Verification

- Use the package's configured scripts and workspace filters.
- Verify typecheck, tests, lint, and formatting for the touched package when configured.
- For failures, quote the exact diagnostic, fix the model or boundary, and rerun the relevant check.
