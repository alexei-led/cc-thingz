# TypeScript and JavaScript Test Performance

Use this for `performance` mode or any TypeScript or JavaScript test suite that
is too slow for an agent feedback loop. The host skill owns the generic
performance workflow and quality guardrails. This file adds JS and TS runner
specific tactics that apply to Vitest, Jest, Bun, Node test runner, and similar
tools.

## Focused commands

Use the project runner first. Examples only:

```bash
vitest run path/to/file.test.ts -t "case name"
jest path/to/file.test.ts -t "case name" --runInBand
bun test path/to/file.test.ts
node --test path/to/file.test.ts
npm test -- --runTestsByPath path/to/file.test.ts
```

Prefer related or changed-file modes when the runner supports them. Keep the full
suite for the final gate or CI.

## Coverage and debug flags

- Keep coverage off the hot path. Coverage instrumentation is for reporting, not
  every edit loop.
- Keep expensive debug flags off the hot path. For Jest, `--detectOpenHandles`
  implies serial execution and has a significant performance penalty.
- Use coverage and open-handle diagnostics only when the task needs them.

## Worker and isolation balance

- Tune worker count instead of assuming more workers is faster. CPU, memory,
  transform cost, database limits, and DOM environments can all make fewer workers
  faster.
- Treat worker-only failures as isolation defects unless evidence says otherwise.
- Use per-worker resources for mutable external state: ports, temp dirs,
  databases, queues, local storage, and fixed filenames.
- Disable file isolation only when tests clean their globals and the affected
  project is safe without isolation. Do not trade determinism for speed.

## Transform, import, and setup cost

- If the runner reports transform, import, setup, or environment time, optimize
  the largest bucket first.
- Move heavy setup out of per-file setup when it can be built once and copied or
  reset cheaply.
- Avoid importing browser, DOM, framework, database, or bundler-heavy modules in
  pure logic tests.
- Keep global setup and preload scripts minimal. They run even when the focused
  test does not need them.
- Use explicit test roots and ignore patterns so discovery does not scan build
  output, fixtures, vendor trees, examples, or end-to-end suites.

## Environment cost

- Use the cheapest environment that preserves behavior. Pure logic should run in
  Node or the runner's default environment, not a DOM environment.
- Scope DOM tests to files that need DOM APIs.
- Do not switch DOM implementations blindly. Faster DOM shims can miss browser
  behavior; use them only when the project already accepts that fidelity tradeoff.

## Time and async

- Replace real sleeps with fake timers, controlled clocks, or poll-until-condition
  helpers with short intervals and hard timeouts.
- Reset only the timers, mocks, modules, handlers, and globals the test changes.
  Blanket reset work can dominate tiny tests.
- Shorten test-only timeouts so failure paths are fast too.

## Slow tiers

- Split slow tests with project markers, directories, or scripts: integration,
  browser, live service, visual, contract, and end-to-end.
- The default local command should run the fast deterministic tier.
- The full gate should still run the slow tiers where they are required.
