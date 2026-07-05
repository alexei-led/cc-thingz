---
description: Idiomatic TypeScript development. Use when writing TypeScript code, Node.js
  services, React apps, or TypeScript design advice. Emphasizes strict typing, boundary
  validation, composition, fast feedback, behavior tests, and project-configured tooling.
  NOT for Go, Python, Rust, plain HTML/CSS/JS, or server-rendered templates (use writing-web).
name: writing-typescript
---

<!-- Pi platform guidance -->
<!-- Use Pi tool names exactly: read, bash, edit, write, ask_user_question, structured_output, todo, subagent, wait, web_search, web_answer, web_research. -->
<!-- Use subagent for delegated work. Use wait to block on async subagent runs only when no independent work remains. -->
<!-- Use ctx7 or npx ctx7@latest through bash when Context7 documentation lookup is required. -->

# TypeScript Development

## Scope

- Use for `.ts` and `.tsx`, Node.js services, React apps, typed APIs, and TypeScript design advice.
- Do not use for Go, Python, Rust, plain HTML/CSS/JS, or server-rendered templates.
- Follow the repository's TypeScript version, tsconfig, package manager, framework, test runner, and lint rules.
- Do not add dependencies or switch frameworks unless the project already uses them or the user approves.

## Reference Reads

- Read only the references needed for the task.
- Read `references/principles.md` for non-trivial TypeScript changes or reviews.
- Read `references/patterns.md` for data models, validation, async flow, or module boundaries.
- Read `references/react.md` for `.tsx`, hooks, component state, forms, performance, or React tests.
- Read `references/testing.md` before adding or changing TypeScript tests.
- Read `references/linting.md` before changing lint config, lint commands, or slow lint workflows.

## Defaults

- Preserve strict typing; do not weaken compiler options to pass checks.
- Use `unknown` for untrusted input. Avoid `any`; isolate it only for unavoidable interop.
- Validate API, JSON, env, storage, and form data at the boundary before typed use.
- Use discriminated unions for variants, async state, and domain states.
- Use guard clauses and focused helpers. Avoid deep nesting, global state, and mixed concerns.
- Use the project's error conventions; prefer unions or `Result` for recoverable failures.
- Pass dependencies explicitly; avoid inheritance, singletons, and hidden module state.
- Avoid unsafe casts, non-null assertions, broad index signatures, boolean-flag state, and new app enums where literal unions fit.

## Comments and JSDoc

- Use JSDoc or TSDoc for exported APIs and non-obvious public properties or methods.
- Avoid merely restating property, parameter, or type names.
- Add implementation comments only for non-obvious constraints, invariants, side effects, tradeoffs, or interoperability quirks.
- Keep comments short. Move longer rationale to docs, issue links, or design notes.
- Do not comment obvious code.
- Keep tests readable without comments; add one only for unobvious fixtures, timers, concurrency, browser setup, or regression context.

## Testing and Verification

- For behavior changes, include success and failure tests. For React, cover affected user-visible states.
- Use focused test, typecheck, and lint commands for the changed file, package, or workspace while editing.
- Run the project's configured typecheck, tests, lint, and format checks for the changed package or workspace before final output.
- Keep coverage, end-to-end tests, and expensive debug diagnostics off the hot path unless they are the task.
- Report checks run, failures, and unchecked risks. Do not claim success without a clean check or an explicit reason it was skipped.

## Failure Handling

- If project root is unclear, identify the nearest `package.json` and `tsconfig.json`; in monorepos, state the selected package.
- If strict compiler options are absent, do not silently weaken new code. State the gap and keep the change locally type-safe.
- If validation needs a schema/form library not already used, ask before adding it; otherwise use a narrow type guard.
- If typecheck or tests fail, quote the exact diagnostic or failing assertion, state the cause, and fix the type/model boundary before widening types.
- Do not run destructive shell commands. For broad or risky changes, state the risk and ask before acting.

## Final Response

- Files changed:
- Checks:
- Skipped checks:
- Risks/follow-ups:
