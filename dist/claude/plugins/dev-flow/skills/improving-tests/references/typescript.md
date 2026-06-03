# TypeScript Test Slice

Use this only for TypeScript or JavaScript test work. The host skill owns scope,
workflow, and output.

## Commands

Use project commands first. If none exist, choose the narrowest useful command:

```bash
bun test
bun test --coverage
bun run tsc --noEmit
npm test
```

Run coverage only for coverage mode or when review needs it. Type errors in test
files are blocking; quote the relevant output.

## Learn project patterns

Before changing tests:

- Read nearby `*.test.ts`, `*.spec.ts`, or equivalent files.
- Check shared test utilities under `tests/`, `__tests__/`, or project-specific dirs.
- Note framework, mock, `describe`, and `it.each` conventions.
- Follow project conventions unless they are the problem.

## Behavior seams

Prefer public module, API, CLI, component, or service boundaries. For React, test
user-visible behavior through Testing Library queries, not component state or hooks.

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

## Failure handling

- Test runner failures and type errors are blocking.
- If coverage is unavailable, note the gap and continue with visible test review.
- If no project test pattern exists, state that and apply general framework practices.
