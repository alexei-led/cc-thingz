---
{"description":"Idiomatic TypeScript development. Use when writing TypeScript code, Node.js services, React apps, or TypeScript design advice. Emphasizes strict typing, boundary validation, composition, fast feedback, behavior tests, and project-configured tooling. NOT for Go, Python, Rust, plain HTML/CSS/JS, or server-rendered templates (use writing-web).","name":"writing-typescript"}
---
<!-- Pi platform guidance -->
<!-- Use installed Pi tool names exactly. Installed extensions may add toolsets such as Task*, Monitor*, and Loop*; use the visible tool names exactly and do not translate them to Claude syntax. -->
<!-- Prefer Task* over `todo` when task-tracking tools are available; `todo` is the cc-thingz fallback. Prefer MonitorCreate for long-running or background commands and LoopCreate for scheduled or event-driven follow-up instead of Bash sleep/poll loops. -->
<!-- Use subagent for authorized delegation. Ordinary async subagents notify the parent natively; yield instead of polling or calling bg_wait merely because a child is active. Use blocking bg_wait only for provider, detached, or other background work without a native notification when a required same-turn result is needed. -->
<!-- Current pi-subagents uses one model per launch; do not configure fallbackModels. A different model requires an explicit new launch after inspecting the failed run and partial work. Use the owning workflow/controller for retries. -->
<!-- Use ctx7 or npx ctx7@latest through bash when Context7 documentation lookup is required. -->


# TypeScript Development

Follow the repository's TypeScript version, tsconfig, package manager, framework, and test runner. In a monorepo, work from the nearest `package.json` and `tsconfig.json` and name the package you chose.

## Defaults

- Never weaken compiler options to pass a check. New configs enable `strict`, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`, `useUnknownInCatchVariables`, `noImplicitOverride`, and `noFallthroughCasesInSwitch`.
- Treat HTTP responses, JSON, env, storage, form data, and SDK output as `unknown`. Narrow at the boundary with the project's schema library or a small type guard; never cast `await res.json()` to a domain type.
- Avoid `any`, `as` casts, non-null `!`, and broad index signatures unless a runtime check or an external type gap justifies them.
- Discriminated unions for variants and async state, with an exhaustive `never` check. Literal unions or `as const` arrays instead of new enums. `satisfies` for config maps.
- Result unions for recoverable failures callers must branch on; throw `Error` instances otherwise.
- Pass dependencies as parameters; no singletons or hidden module state. Thread `AbortSignal` through work that can outlive its caller.
- Ask before adding a schema, form, query, or state library the project does not already use.

## React

- Plain function components, not `React.FC`. Type `children` as `ReactNode`.
- Derive state during render. Fix stale closures instead of suppressing exhaustive-deps.
- Add `memo`, `useMemo`, or `useCallback` only for measured cost or a real identity need.
- Validate fetched data in the fetcher, not in render. Custom hooks throw when their provider is missing.

## Tooling

Typecheck with the project script or `tsc --noEmit`. Use one formatter and one linter per file; the selection order is in linting.md.

## References

- [testing.md](references/testing.md): read when adding or changing tests, including React component tests.
- [linting.md](references/linting.md): read when choosing a formatter or linter, changing lint config, or diagnosing slow lint.

Done when the relevant build/test/lint checks pass on what you changed, or you name each check that did not run and why.
