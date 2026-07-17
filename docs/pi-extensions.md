# Pi package

Agent Bundler produces one aggregate Pi package at `dist/pi/`. Release builds
archive that package as `cc-thingz-pi.tgz`.

## Generated resources

The package registers:

- `extensions/agentbundler-hooks.ts` — the generated typed hook adapter;
- `extensions/ask-user-question.ts`, `extensions/structured-output.ts`, and
  `extensions/todo.ts` — declaratively bundled native tool extensions;
- `node_modules/pi-subagents/src/extension/index.ts` — the bundled subagent
  runtime;
- `skills/` — all Pi-eligible cc-thingz skills;
- `agents/` — advisor, engineer, reviewer, and runner definitions;
- `hooks/hooks.v1.json` — normalized hook data consumed by the adapter.

`pi-subagents` and its runtime dependencies are present in
`bundledDependencies`, so a fresh installation does not require a separate
`pi install npm:pi-subagents` step.

Install a release archive in a project:

```bash
pi install ./cc-thingz-pi.tgz -l
```

For local development, build and install the generated package root:

```bash
make build
pi install "$(pwd)/dist/pi" -l
```

Run `/reload` or restart Pi after replacing a linked package.

## Generated hook coverage

The aggregate adapter currently handles these portable events:

- session start;
- prompt submission;
- pre-tool command and write checks;
- post-tool linting;
- stop/test handling.

The Pi package includes file protection and git guardrails. Hook subprocesses
receive only the environment variables declared in each hook descriptor plus
Agent Bundler's safe runtime baseline. They do not inherit arbitrary parent
secrets.

## Native extension assets

`src/plugins/pi/extensions/` is a declarative native-resource asset. Its
`.agentbundler/asset.json` registers only these entrypoints:

- `extensions/ask-user-question.ts`;
- `extensions/structured-output.ts`;
- `extensions/todo.ts`.

Agent Bundler copies the complete asset tree to the Pi package root and registers
only those paths in `package.json#pi.extensions`. Add an entrypoint only when
its relative imports and runtime contract are complete. Do not copy files into
`dist/` after generation.

## Source-only legacy extensions

`src/pi-extensions/` retains the incomplete synthetic-hook stack:

- `hook-runner` and its hook configuration;
- `permission-gate`;
- `plan-mode`;
- shared hook bridge code.

`permission-gate` and `plan-mode` call the shared bridge. Without a complete,
bundled `hook-runner` configuration they cannot safely be registered: permission
decisions fail closed and plan exit can wait for the outer hook timeout. Their
source tests remain, but the release package does not expose them.

## Verification

```bash
agbun check --root .
pytest -q tests/test_agentbundler_hooks.py tests/test_agentbundler_release.py
make lint-typescript
make test-ts
```

The release tests verify the generated hook inventory, agent frontmatter,
bundled Pi dependency, deterministic archive contents, and an isolated local
`pi install` when the Pi CLI is available.

See [Agent Bundler migration status](agentbundler-gaps.md) for unsupported
lifecycle events and remaining vendor gaps.
