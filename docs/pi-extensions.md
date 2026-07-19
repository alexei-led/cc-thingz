# Pi package

Agent Bundler produces the aggregate Pi package at `dist/pi/`; releases archive
it as `cc-thingz-pi.tgz`. The development `package.json` also carries a merged
root compatibility manifest whose resource paths point into `dist/pi`.

## Registered extensions

`package.json#pi.extensions` registers:

- `extensions/agentbundler-hooks.ts` — typed portable-hook adapter;
- `extensions/ask-user-question.ts`;
- `extensions/hook-runner/index.ts`;
- `extensions/permission-gate.ts`;
- `extensions/plan-mode/index.ts`;
- `extensions/structured-output.ts`;
- `extensions/todo.ts`.

cc-thingz does not bundle third-party Pi extensions. Install `pi-subagents`
separately if you want the packaged `cc-thingz.*` agents:

```bash
pi install npm:pi-subagents
pi install ./cc-thingz-pi.tgz -l
```

The native extensions, skills, and hooks work without `pi-subagents`; only the
packaged agent definitions require its runtime.

For local development through the repository root:

```bash
make build
pi install npm:pi-subagents -l  # required only for cc-thingz.* agents
pi install "$(pwd)" -l
```

The root install exercises the same layout used by
`pi install git:github.com/alexei-led/cc-thingz`. Installing `dist/pi` remains useful
for testing the target-native package:

```bash
pi install "$(pwd)/dist/pi" -l
```

`-l` writes the package to project settings. Restart Pi or run `/reload` after
changing a loaded package.

## Portable hooks

`hooks/hooks.v1.json` and `agentbundler-hooks.ts` handle portable session-start,
prompt-submit, pre-tool, post-tool, stop, file-protection, git-guardrail,
smart-lint, and test-runner descriptors. Hook subprocesses receive Agent
Bundler's safe baseline plus the hook's declared environment allowlist.

## Pi compatibility runner

`src/plugins/pi/extensions/extensions/hooks.json` is intentionally small. The
native `hook-runner` loads only Pi-specific defaults:

- `SessionStart`, `Stop`, and `SessionEnd` → asynchronous `ccgram hook`;
- `ExitPlanMode` → `hooks/revdiff-plan-review.py` for plan-mode review;
- `Notification` → `hooks/notify.sh`.

The runner also merges compatible global/project `.pi/{settings,hooks}.json`
and package contributions. It must not list portable hooks already dispatched
by `agentbundler-hooks.ts`; otherwise they run twice.

`permission-gate` uses the runner's synthetic PermissionRequest and
PermissionDenied events. Safe commands pass. Dangerous `rm -rf`, `sudo`, and
`chmod/chown 777` commands require UI confirmation, fail closed headlessly, and
reject a hook-supplied replacement that remains dangerous.

`plan-mode` supplies `/plan`, read-only tools, plan progress, and synthetic
ExitPlanMode review. Revdiff denial, an updated plan, and timeout behavior flow
through the compatibility runner.

### Revdiff plan review

Pi has no native `ExitPlanMode` event. The `plan-mode` extension detects the
last assistant plan on `agent_end`, then invokes a synthetic `ExitPlanMode`
`PreToolUse` hook when the user selects **Execute the plan**.

Install the revdiff Pi package as well as the `revdiff` binary:

```bash
pi install git:github.com/umputun/revdiff
```

The review loop is:

1. Run `/plan` and ask the agent to plan the work.
2. Select **Execute the plan** after the agent emits a numbered `Plan:` block.
3. Annotate the plan in revdiff and quit the review.
4. With annotations, execution stays blocked and the annotations are sent back
   to the agent so it revises the plan.
5. Select **Execute the plan** again. Revdiff compares the revision with the
   previous reviewed snapshot.
6. Quit without annotations to approve the plan and start execution.

If the revdiff package is absent, the optional wrapper fails open. A review
subprocess timeout fails closed and leaves plan mode active.

## Native source layout

`src/plugins/pi/extensions/` is one declarative native-resource asset.
`.agentbundler/asset.json` lists extension entrypoints; Agent Bundler copies the
complete tree to the Pi root while registering only those entries. Supporting
modules, compatibility `hooks.json`, and hook scripts are copied but are not
extension entrypoints.

Do not copy files into `dist/` after generation. See
[Agent Bundler port status](agentbundler-gaps.md) for current vendor and
upstream boundaries.

## Verification

```bash
agbun build --root .
agbun check --root .
pytest -q tests/test_agentbundler_hooks.py tests/test_agentbundler_release.py \
  tests/test_root_compatibility.py
make lint-typescript
make test-ts
```

The root compatibility suite performs isolated Pi local-path and Git installs,
then queries Pi RPC commands to prove native extensions and skills load. It also
installs standalone `pi-subagents` and proves the packaged agents are discovered
without a duplicate tool provider. `pi list` by itself is not a resource-loading
assertion.
