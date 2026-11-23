# Pi package

Agent Bundler produces the aggregate Pi package at `dist/pi/`; releases archive
it as `cc-thingz-pi.tgz`. The development `package.json` also carries a merged
root compatibility manifest whose resource paths point into `dist/pi`.
The native extensions require Pi **1.0.2 or later in the 1.x series**. The
repository-root peer contracts use `^1.0.2`; Agent Bundler does not render peer
dependencies into the target-root archive manifest, so archive users must check
the host version themselves. The lockfiles record the tested baseline. The permission gate also requires the
pinned `web-tree-sitter` runtime package and a bundled `tree-sitter-bash`
WASM grammar. Managed Git installs resolve the runtime dependency automatically.

## Registered extensions

`package.json#pi.extensions` registers:

- `extensions/agentbundler-hooks.ts` — typed portable-hook adapter;
- `extensions/ask-user-question.ts`;
- `extensions/hook-runner/index.ts`;
- `extensions/permission-gate.ts`;
- `extensions/plan-mode/index.ts`.

cc-thingz does not bundle third-party Pi extensions. Install `pi-subagents`
separately if you want the packaged `cc-thingz.*` agents:

```bash
pi install npm:pi-subagents
pi install git:github.com/alexei-led/cc-thingz@v8.2.0
```

The native extensions, skills, and hooks work without `pi-subagents`; only the
packaged agent definitions require its runtime.

Pi 1.0.2 cannot load a `.tgz` path directly as an extension package. To test a
release archive, extract it to an isolated directory and prepare dependencies
with `npm install --omit=dev --ignore-scripts`. Then point an isolated Pi
configuration at that directory.
Use published Git tags for normal managed installations.

For isolated local development testing through the repository root:

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

## Agent names and defaults

Pi runtime names for the packaged agents are package-qualified:

```text
cc-thingz.advisor
cc-thingz.engineer
cc-thingz.reviewer
cc-thingz.runner
```

Use `cc-thingz.reviewer` when the builtin `pi-subagents` reviewer is also
loaded. The unqualified `reviewer` name is ambiguous in that configuration.
The Pi reviewer is read-only, inherits project instructions, and exposes the
review, test, documentation, and spec-flow skills.

## Models and retries

This guidance applies to current pi-subagents releases with the single-model
launch contract. Install the current `pi-subagents` release rather than pinning
an exact version; older releases that still support `fallbackModels` need their
version-matched documentation. The compatibility smoke tests use the unversioned
`npm:pi-subagents` package spec.

Current releases reject `fallbackModels` in agent definitions, overrides, and
watchdog settings. Delete the key, including empty arrays; there is no replacement
fallback-chain setting. Each launch resolves one model and returns its outcome.

For a provider or quota failure:

1. Record the failed run ID, error, selected model, and working directory.
2. Confirm the child stopped; inspect its outputs and partial diff before replaying
   work. Do not repeat completed writes or external actions blindly.
3. Start a new run with an explicit available `model`, preserving the task's tools,
   skills, isolation, and approval scope. Link it to the failed run in the handoff.
   A resume keeps the original model contract; it is not a model-switch mechanism.
4. Use the owning workflow/controller for managed runs. If it cannot express the
   retry, stop and ask the operator; do not bypass it with a CLI or another agent.

Do not retry loader, configuration, permission, or code failures on another model.
Do not turn these steps into an automatic retry loop. Ordinary async subagents
notify the parent natively; yield instead of polling or calling `bg_wait` merely
because a child is active. Use blocking `bg_wait` only for provider, detached,
or other background work without a native notification when a required same-turn
result is needed.

See the upstream [model selection and retries
documentation](https://github.com/nicobailon/pi-subagents/blob/main/docs/models.md)
for the current contract.

## Structured questions

`ask_user_question` remains a model-facing tool with the same question schema
and answer `details`. It is `model-only`: invoke it directly, not from Code Mode.
The model-facing text contains the answer JSON, including machine values.

- Single choices use native `ctx.ui.select`, with numbered labels and optional
  descriptions. Duplicate labels retain distinct option values.
- Free text and **Other / type something** use native `ctx.ui.input`.
- Pi has no native multi-select dialog. Multiple choices use a blank native input
  with comma-separated option numbers or labels. Custom values are accepted only
  when `allowOther` permits them; duplicate selections are removed.
- These flows work with TUI and RPC clients. Escape/cancellation stops subsequent
  questions. Empty input is an empty answer, not cancellation.

## Automatic tests

The Stop test runner is disabled by default. To enable focused automatic tests
in a trusted Pi project, add `"automaticTests": true` to its `.pi/settings.json`.
Remove the setting or set it to `false` to disable the runner. The setting is
read from the session working directory before each turn. It does not run
`make check` or replace explicit tests, Git hooks, or CI.

For Claude Code, set `"env": {"SKIP_TESTS": "0"}` in the project's
`.claude/settings.local.json`. Automatic results are advisory; the agent must
choose and report relevant verification. The hook still starts when disabled.

## Portable hooks

`hooks/hooks.v1.json` and `agentbundler-hooks.ts` handle portable session-start,
pre-tool, post-tool, stop, file-protection, git-guardrail,
smart-lint, and test-runner descriptors. Hook subprocesses receive Agent
Bundler's safe baseline plus the hook's declared environment allowlist.

## Pi compatibility runner

The shipped `extensions/hooks.json` is empty. The native runner merges
compatible global/project `.pi/{settings,hooks}.json` and package contributions.
Configure personal messaging, notification, and review integrations at user
scope. Portable hooks already dispatched by `agentbundler-hooks.ts` must not
also be listed here, or they run twice.

See [hook policy](hook-policy.md) for the separate Git and file protection settings.

### Blacklist-only Bash warnings

Normal commands pass by default. The gate does not maintain a safe-command list,
restrict pipeline filters, or block a command just because its syntax is unknown.
Adding an allow rule does not restrict other invocations of the same executable.

The built-in blacklist warns on recognizable local `sudo`, recursive `rm`,
and `chmod/chown` modes ending in `777`. It checks recognized commands in
pipelines and command chains. It recognizes common runner prefixes such as
`xargs` and `timeout`, and executable actions in `find`. Commands inside local
command substitutions and unquoted heredocs are inspected; an executable
produced by an expansion is not classified. Unknown syntax is not itself a warning.

Quoted arguments, interpreter source, and quoted heredoc bodies are data to the
outer shell, not executable commands. Literal warning words inside them do not
trigger built-in confirmation. Unquoted heredocs are checked for local expansion
hazards; recognized commands after a heredoc still get checked. Python, Node, shell `-c`
payloads, and remote programs are intentionally not inspected for indirect
effects. They can delete files or launch privileged commands without a built-in
warning. This is an approval aid, not a sandbox. Bounded Tree-sitter parsing
recognizes shell syntax, but unsupported syntax, parse recovery, or exhausted
inspection budgets can leave later actions unclassified rather than blocking
normal work.

Text triggers still dispatch PermissionRequest hooks when a built-in warning is
suppressed, except for the existing literal display/terminal exemption for
`echo`, `printf`, `agtermctl`, and `herdr`. Explicit denies run first; other hook
vetoes and timeouts remain in force.
A recognized warning needs UI confirmation, a hook allow, or an eligible exact
exception. Without UI or an eligible exception, the warning blocks.

[Design sources, real-session tests, and verification limits](permission-gate-testing.md)
describe how this behavior is checked.

### Optional warning exceptions and explicit denies

Use `permissionGate` in user `~/.pi/agent/settings.json` or trusted project
`.pi/settings.json`. Reload or restart to apply changes. For example, this
trusted-project exception permits one exact cleanup invocation:

```json
{
  "permissionGate": {
    "allow": [
      { "match": "Bash(rm -rf ./build)", "headless": true }
    ]
  }
}
```

An allow rule only waives a warning for a complete literal invocation. It does
not make other commands forbidden. A standalone `*` matches one nonempty
argument, not a shell-string tail; in allow rules that argument must not begin
with `-`. Separate exceptions are not automatically composed across pipelines
or command chains.

A user `deny` list uses the same format and blocks positively matched command
shapes, including recognized commands within chains and pipelines. Denies win
over allows. Deny matching accepts option arguments for `*`. Unmatched or
unrecognized syntax does not itself trigger a denial. These rules cannot enforce
a program-wide ban across every shell encoding or interpreter.

Projects can add allows only, and only while trusted. An absent or malformed
project policy adds no exceptions; malformed user policy reports an error and
blocks Bash until repaired. `/permissions` shows effective rules and their source.
Hook-supplied replacements are checked again against the blacklist and user
denies.

Existing SSH grants may remain, but are not required merely because a quoted
remote payload contains `sudo`. They are not a destination ACL: use cloud IAM
and SSH access controls for that.

Pi runs the original command through its configured shell after `tool_call`.
Shell startup, `shellCommandPrefix`, executable lookup, or later extensions may
change execution. Use OS isolation for enforcement; this gate does not cover
arbitrary deletion methods, MCP calls, or non-Bash tools.

`Stop` and `StopFailure` retain their `agent_end` behavior. Idle notifications
run only on `agent_settled`, after automatic retries and queued continuations.
`PreCompact` and `PostCompact` receive `trigger: event.reason` (`manual`,
`threshold`, or `overflow`), independent of who supplied the summary.

Shutdown first cancels and drains session-owned hooks. Synchronous `SessionEnd`
hooks are awaited. Async `SessionEnd` hooks run best-effort under a detached
POSIX supervisor using `node` on `PATH` that owns the configured deadline
(default 30 seconds) and
terminates the hook process group, with a 1.5-second forced-kill grace. These
hooks have no departing-session UI or captured output/telemetry. No temporary
files are created. Invalid or overflowing timer values are not launched.
A missing Node executable logs a launch error and skips the async hook without
blocking shutdown; compiled Pi users must also install Node for this flow.

## Planning and task tracking

`plan-mode` supplies `/plan`, read-only tools, and plan progress. When the
user selects **Execute the plan**, it invokes a synthetic `ExitPlanMode`
`PreToolUse` hook. User-configured hooks may block, annotate, or update the
plan; no Revdiff wrapper or other review integration is bundled.

Use the separate `@tintinweb/pi-tasks` package for task tracking. cc-thingz no
longer registers `todo` / `/todos` or the fixed-schema `structured_output`
demonstration. Existing saved session entries are not deleted.

For durable plan execution, `@alexeiled/pi-plan-exec` uses native
`pi-subagents`; it does not require cc-thingz, pi-tasks, or
`pi-subagents-bridge`. Bridge may still serve a separate pi-tasks
`TaskExecute` integration. Check consumers and unresolved operations before
retiring it; never delete recovery records as package cleanup.

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
