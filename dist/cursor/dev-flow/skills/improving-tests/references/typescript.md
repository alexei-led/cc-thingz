# TypeScript and JavaScript Tests

Use writing-typescript for toolchain commands and the project's runner.

## Patterns

- `it.each`/`test.each` with object cases for multi-field inputs.
- React: test user-visible behavior with Testing Library. Query by role, then label, then text; test ID last. Prefer `user-event`; use async queries for async state. Cover loading, error, empty, and permission states that matter.
- Snapshots only for complex, stable output.
- Network: MSW or the project's HTTP fakes. Type mocks (`vi.mocked()`) so contract drift fails to compile. Restore mocks per project convention.

## Speed

- Use the runner's related or changed-file mode in the edit loop.
- Coverage and Jest `--detectOpenHandles` (which forces serial execution) are diagnostics, not the default loop.
- Tune worker count by measurement: transform cost, memory, DOM environments, and database limits often make fewer workers faster.
- Disable per-file isolation only when tests clean their globals. Never trade determinism for speed.
- When the runner reports transform, import, setup, or environment time, cut the largest bucket first. Keep global setup and preloads minimal; they run for every focused test.
- Explicit test roots and ignores, so discovery skips build output, fixtures, vendor trees, and e2e suites.
- Pure logic runs in the Node environment, not a DOM one. Scope DOM environments to the files that need them; do not swap DOM implementations unless the project accepts the fidelity loss.
- Fake timers or poll-until-condition helpers instead of sleeps. Reset only the timers, mocks, and modules a test changed; blanket resets dominate tiny tests.
