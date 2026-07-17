# TypeScript Test Slice

Use this only for TypeScript or JavaScript test work. The host skill owns scope,
workflow, and output. For `performance` mode or slow-suite work, also read
`typescript-performance.md`.

## Commands

Use project commands first. If none exist, choose the narrowest useful command:

```bash
bun test path/to/file.test.ts
vitest run path/to/file.test.ts
jest path/to/file.test.ts -t "case name" --runInBand
node --test path/to/file.test.ts
bun test
npm test
```

Run coverage only for coverage mode or when review needs it. Keep coverage and
open-handle diagnostics off the hot feedback path. Test runner failures are
blocking; quote the relevant output.

## Learn project patterns

Before changing tests:

- Read nearby `*.test.ts`, `*.spec.ts`, or equivalent files.
- Check shared test utilities under test directories and project-specific helper dirs.
- Note framework, mock, `describe`, and `it.each` conventions.
- Follow project conventions unless they are the problem.

## Behavior seams

Prefer public module, API, CLI, component, or service boundaries. For React, test
user-visible behavior through Testing Library queries, not component state or hooks.

## Fast feedback defaults

- Use the narrowest deterministic file, test name, or related-test command.
- Keep pure logic tests out of DOM or browser environments.
- Keep global setup, preloads, and test utilities small enough that focused runs
  stay focused.
- Treat worker failures as isolation defects unless evidence says otherwise.
- Split integration, browser, live-service, visual, and end-to-end tiers from the
  default local command.

## Parameterized tests

Prefer `it.each`, `test.each`, or the project equivalent when cases share setup and
assertions. Do not force consolidation when separate tests make behavior clearer.
Use object cases for multi-field inputs.

## React and DOM tests

- Query by role first, then label, text, and test ID as last resort.
- Prefer `user-event` over low-level event helpers when testing user behavior.
- Use async queries for async UI state.
- Cover loading, error, empty, success, and permission states when they matter.
- Avoid snapshot tests unless the output structure is complex and stable.

## Mocks

- Mock system boundaries and external services.
- Prefer MSW or project HTTP fakes for network behavior when already used.
- Use `vi.mocked()` or typed helpers when available.
- Verify business-critical mock calls with exact values.
- Use loose matchers only for generated values or true don't-care fields.
- Restore mocks between tests according to project convention.

## Review focus

Flag:

- tests coupled to implementation details, hook state, or incidental calls
- happy-path-only tests for meaningful logic
- duplicate scenarios that can be clearer as parameterized cases
- untyped or loose mocks hiding contract errors
- missing async failure, null/undefined, edge, permission, loading, or empty states
- brittle selectors, snapshots, sleeps, or shared state
- slow transform, import, setup, DOM environment, coverage, or broad discovery in the fast path
- worker-count changes that trade determinism for speed

## Failure handling

- Test runner failures are blocking.
- If coverage is unavailable, note the gap and continue with visible test review.
- If no project test pattern exists, state that and apply general framework practices.
