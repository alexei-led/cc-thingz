# Pi Extensions

Extensions bundled with cc-thingz that run inside [Pi](https://pi.dev). All
extensions install automatically when you `pi install` this package.

## Included Extensions

### hook-runner

Bridges Pi's lifecycle events to the same CC-compatible hook scripts used by
Claude Code, Codex, and Gemini. This is the primary integration point between
Pi and the rest of cc-thingz.

**What it wires:**

| Pi event                   | Hook script         | Behavior                                                      |
| -------------------------- | ------------------- | ------------------------------------------------------------- |
| `session_start`            | `session-start.py`  | Prints project context to chat on startup                     |
| `session_start` / all      | `ccgram hook`       | Tracks sessions in ccgram (async)                             |
| `before_agent_start`       | `skill-enforcer.sh` | Suggests relevant skills before each prompt                   |
| `tool_call` (Write/Edit)   | `file-protector.py` | Blocks writes to protected paths                              |
| `tool_call` (Bash)         | `git-guardrails.sh` | Blocks destructive git commands                               |
| `tool_result` (Write/Edit) | `smart-lint.sh`     | Injects focused lint errors into tool result (LLM feedback)   |
| `agent_end` (`Stop`)       | `test-runner.sh`    | Runs focused tests once after the agent turn                  |
| `agent_end`                | `ccgram hook`       | Tracks session end in ccgram (async)                          |
| `agent_end`                | `notify.sh`         | Fires a macOS idle-prompt notification on every `agent_end`   |
| `input` (slash commands)   | user-configured     | Emits `UserPromptExpansion` hooks before command expansion    |
| `turn_end` (tool batches)  | user-configured     | Emits `PostToolBatch` hooks with per-turn tool call summaries |

**Hook configuration:** default hook wiring is data, not hard-coded. The
package ships `dist/pi/extensions/hooks.json` (generated at build time from
`src/hooks/*/meta.yaml` plus `scripts/build/pi-hooks-external.json`), and
hook-runner loads it at runtime. Sources are merged in this order
(bundled → package → global → project):

- bundled defaults from `dist/pi/extensions/hooks.json`
- per-package contributions via `cc-thingz.hooks` in any installed Pi
  package's `package.json` (auto-discovered under `~/.pi/agent/git/`)
- `hooks` key in global `settings.json` or project `.pi/settings.json`
- dedicated global `hooks.json` or project `.pi/hooks.json`

The global config directory is `PI_CODING_AGENT_DIR` when set, otherwise Pi's
default `~/.pi/agent`. `hooks.json` accepts either the direct hooks map or
`{ "hooks": { ... } }`.

Example in `settings.json`:

```jsonc
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "/usr/local/bin/my-audit.sh",
            "timeout": 10,
          },
        ],
      },
    ],
  },
}
```

Equivalent `hooks.json` form:

```jsonc
{
  "PreToolUse": [
    {
      "matcher": "Bash",
      "hooks": [
        {
          "type": "command",
          "command": "/usr/local/bin/my-audit.sh",
          "timeout": 10,
        },
      ],
    },
  ],
}
```

Hook commands run via `bash -c`, so shell features and PATH resolution work.
User hooks are appended after bundled defaults. The `matcher` field is a
case-insensitive regex matched against the CC tool name (e.g. `Write`, `Bash`,
`MultiEdit`).

Disable bundled defaults while keeping user/project hooks by adding this to
`.pi/hooks.json`:

```jsonc
{
  "hookRunner": {
    "disableBundledHooks": true,
  },
}
```

`smart-lint.sh` is scoped to the edited file set from hook stdin and falls
back to git diff only for small changed-file sets. It formats and lints focused
files first, then uses project fallbacks only for the missing side: package
scripts (`fmt` / `format`, `lint`) before Makefile targets (`fmt`, `lint`). For
C# /.NET, source edits use `dotnet format` on the nearest project or containing
solution with `--include`; `.csproj`, `.sln`, `.props`, and `.targets` edits use
the nearest safe project or solution target. For Java/Kotlin, file-scoped
`google-java-format`, `ktlint --format`, and `detekt --input` run first, with
configured Gradle/Maven Spotless/detekt fallbacks only when needed. Disable
project fallbacks with `HOOK_PROJECT_FALLBACK=0` or a `.nohooks-project` file.

`test-runner.sh` runs on `Stop`, using the edited-file state from
`smart-lint.sh`; it runs focused tests only unless `TEST_RUNNER_FULL=1` is set.
Focused tests use pytest, Go packages, Cargo manifests, Gradle/Maven Java/Kotlin
module filters, `dotnet test` on the nearest obvious test `*.csproj`, else the
containing `*.sln`, else the nearest `*.csproj`, Vitest related tests, Jest
related tests, Bun tests, or Bats where applicable. If a changed file lives
under a nearest non-root Makefile with `test`, `tests`, `check`, or `verify`,
that target runs before the generic language runners. Otherwise focused runners
try first, then package scripts (`test`, `tests`, `check`, `verify`).
`TEST_RUNNER_FULL=1` runs one project-level target: root Makefile,
then Go/Rust/Java/Kotlin/C#/.NET/Python runners, then package scripts selected by yarn/bun/npm lockfiles.

Mute individual hooks (bundled or user) by basename without disabling the
whole bundled set:

```jsonc
{
  "hookRunner": {
    "disabledHooks": ["smart-lint.sh", "test-runner.sh"],
  },
}
```

`disabledHooks` is merged from every config file that hook-runner reads
(global and project). Entries still appear in `/hooks` → **Show active hooks**
with a `(disabled)` marker so they remain discoverable.

**Package-contributed hooks:** any Pi package installed via `pi install` may
register hooks declaratively. Add a `cc-thingz.hooks` field to the package's
`package.json` mirroring the standard hook config shape:

```jsonc
{
  "name": "my-pi-plugin",
  "cc-thingz": {
    "hooks": {
      "PostToolUse": [
        {
          "matcher": "Write|Edit",
          "hooks": [
            { "type": "command", "command": "/usr/local/bin/my-audit" },
          ],
        },
      ],
    },
  },
}
```

Hook-runner scans `~/.pi/agent/git/<host>/<org>/<repo>/package.json` at
session start and merges contributions under `source: "package"`. The
`/hooks` UI labels them accordingly. This removes the need for cc-thingz
edits when a third-party Pi extension wants to ship a hook.

**Progress protocol:** long-running hooks may emit lines on stderr matching
`^^PROGRESS <0-100> <message>` to report progress. Hook-runner strips the
markers from the stderr that reaches the LLM feedback loop and surfaces the
last update through an internal `onProgress` callback. Hooks that don't emit
the marker behave unchanged.

**Telemetry:** every hook run appends a JSONL line to
`~/.pi/agent/logs/hooks.log` recording `ts`, `hook`, `event`, `source`,
`exit_code`, `duration_ms`, `timed_out`, and `stderr_head` (first 500
characters). Useful for diagnosing flaky hooks. Disable by setting
`PI_HOOKS_DISABLE_TELEMETRY=1` in the environment. The writer is
best-effort — telemetry failures never break dispatch.

Use `/hooks` in Pi for an interactive TUI:

- **Show active hooks** — lists every loaded hook grouped by event, with its
  matcher, source (`bundled` / `global` / `project` / `package`), and disabled status.
  `package` is for hooks contributed by installed Pi packages via the
  `cc-thingz.hooks` field in their `package.json` (auto-discovered at session start).
- **Toggle individual hook** — pick a hook from the list, then choose whether
  to record the toggle in project (`.pi/hooks.json`) or global
  (`~/.pi/agent/hooks.json`) `hookRunner.disabledHooks`.
- **Disable/Enable bundled hooks (project)** — flips
  `hookRunner.disableBundledHooks` in `.pi/hooks.json`.
- **Edit project hooks (`.pi/hooks.json`)** — opens the project config in the
  TUI editor; saves are JSON-validated and trigger a reload.
- **Edit global hooks (`~/.pi/agent/hooks.json`)** — same flow for the global
  scope so the same hook can apply across projects.

**Synthetic event bridge for extensions:** other Pi extensions can invoke
hook-runner directly via `cc-hooks:invoke` event-bus channel to trigger
first-class CC hook events not emitted natively by Pi. Payload shape:

```ts
pi.events.emit("cc-hooks:invoke", {
  hookEventName: "ConfigChange", // any supported synthetic event
  stdin: {
    session_id: ctx.sessionManager.getSessionId(),
    cwd: ctx.cwd,
    hook_event_name: "ConfigChange",
    source: "project_settings",
    file_path: `${ctx.cwd}/.pi/settings.json`,
  },
  onResult: (result) => {
    // { blocked?, reason?, additionalContext?, ... }
  },
});
```

Additional compatibility behavior:

- `find` tool is exposed to hooks as CC tool name `Glob`
- `subagent` tool is exposed as `Agent`
- `ask_user_question` is exposed as `AskUserQuestion`
- plan-mode emits a synthetic `PreToolUse` event with
  `tool_name: ExitPlanMode` when the user picks **Execute the plan**
- native extra hooks:
  - `InstructionsLoaded` (session-start snapshot of loaded AGENTS/CLAUDE/rules files)
  - `CwdChanged` (when cwd changes between turns)
  - `StopFailure` (when assistant turn ends with `stopReason: error`)
- extensions can emit synthetic CC-style hook events through Pi's event bus channel `cc-hooks:invoke`
  for additional first-class events such as:
  `Setup`, `TeammateIdle`, `ConfigChange`, `FileChanged`, `WorktreeCreate`,
  `WorktreeRemove`, `Elicitation`, `ElicitationResult`, `TaskCreated`,
  `TaskCompleted`, `PostToolBatch`, `UserPromptExpansion`

**Exit code semantics** (same as Claude Code):

- `0` — allow; stdout shown to user (`SessionStart`) or injected as LLM
  context (`UserPromptSubmit`)
- `1` — non-blocking error; logged and shown to user, execution continues
- `2` — significant: blocks the tool call (`PreToolUse`), injects stderr into
  tool result so the LLM self-corrects (`PostToolUse`), blocks slash-command
  expansion (`UserPromptExpansion`), injects context before the prompt
  (`UserPromptSubmit`), or — for `Stop` — surfaces stderr as an agent-visible
  message that triggers a follow-up turn (handled via
  `sendHookMessageToAgent` in `hook-runner/index.ts`).

#### Revdiff plan-review integration (Pi + hook-runner)

The bundled `hooks.json` includes a default `PreToolUse` hook for
`ExitPlanMode`:

```jsonc
{
  "matcher": "ExitPlanMode",
  "hooks": [
    {
      "type": "command",
      "command": "${PI_HOOKS_DIR}/revdiff-plan-review.py",
      "timeout": 1740,
    },
  ],
}
```

The wrapper is optional and safe by default:

- If the `revdiff` package is not installed, it exits cleanly and plan
  execution proceeds.
- If installed, it resolves
  `plugins/revdiff-planning/scripts/plan-review-hook.py` from:
  - project-local `.pi/git/github.com/umputun/revdiff/...`
  - `PI_PACKAGE_DIR` candidates
  - global `PI_CODING_AGENT_DIR/git/github.com/umputun/revdiff/...`
- It sets the Claude-compatible environment expected by `revdiff-planning`:
  `CLAUDE_PLUGIN_ROOT`, `CLAUDE_PROJECT_DIR`, and `CLAUDE_PLUGIN_DATA`.
- `revdiff-planning` preserves the Claude Code loop: annotations return deny
  (`exit 2`), Pi keeps plan mode active, and the model revises the plan before
  trying `ExitPlanMode` again.

Install revdiff to activate the loop:

```bash
pi install git:github.com/umputun/revdiff
```

Requires the `revdiff` binary on `PATH` and a supported launcher environment
from the revdiff package. Re-run the plan loop until hook output is clean, then
execute.

Supported CC hook events in this Pi bridge:

- Native mappings: `SessionStart`, `SessionEnd`, `SubagentStart`, `Stop`,
  `StopFailure`, `Notification`, `PreToolUse`, `PostToolUse`,
  `PostToolUseFailure`, `PostToolBatch`, `UserPromptSubmit`,
  `UserPromptExpansion`, `PreCompact`, `PostCompact`, `InstructionsLoaded`,
  `CwdChanged`
- Synthetic via `cc-hooks:invoke`: `Setup`, `PermissionRequest`,
  `PermissionDenied`, `TaskCreated`, `TaskCompleted`, `TeammateIdle`,
  `ConfigChange`, `FileChanged`, `WorktreeCreate`, `WorktreeRemove`,
  `Elicitation`, `ElicitationResult`
- Reserved for CC schema compatibility but **not currently emitted by Pi**:
  `SubagentStop`. Hooks configured under this key load but never fire — Pi
  has no subagent-stop runtime event yet. Use `Stop` / `StopFailure` for the
  outer agent turn instead.

`FileChanged`, `WorktreeCreate/Remove`, and MCP elicitation events are extension-driven in Pi (no built-in runtime event), so emit them through the synthetic bridge when your integration owns those flows.

### ask-user-question

Registers an `ask_user_question` tool that lets the LLM ask the user
structured questions (single-select, multi-select, or free text). Used by
`smart-lint.sh` when it needs a decision before applying a fix.

Selectable prompts keep choices visible by wrapping and capping long question
text. Single-select questions render as a navigable selector; multi-select
questions open an editor with capped question text, numbered options, and
comma-separated input guidance.

No configuration.

### permission-gate

Intercepts `bash` tool calls matching dangerous patterns (`rm -rf`, `sudo`,
`chmod/chown 777`) and prompts the user before proceeding. In non-interactive
mode, blocks automatically.

Also emits synthetic hook events through `cc-hooks:invoke`:

- `PermissionRequest` before prompting (hook can allow, deny, or patch command)
- `PermissionDenied` after a deny/block path

Hook timeouts for `PermissionRequest` fail closed.

No configuration needed. If you want to disable it, remove or rename the
extension after install.

### plan-mode

Adds a plan mode that intercepts the agent's plan output, extracts numbered
steps, and surfaces a progress tracker in the Pi TUI. Bash commands are
restricted to an allowlisted read-only set while plan mode is active.

On **Execute the plan**, plan-mode emits synthetic `PreToolUse` with
`tool_name: ExitPlanMode` to support hook-based plan review (for example,
revdiff plan-review loop). Empty plan content skips the hook (fail-open).
Review hook timeouts block exit (fail-closed); align per-entry `timeout` in
`hooks.json` to fire before the 30-minute outer wait.

No configuration.

### structured-output

Registers a `structured_output` tool for the LLM to emit machine-readable
JSON. Used by skills that need to pass structured data to follow-on tools.

No configuration.

### subagent

Provides `spawn_subagent`, `steer_subagent`, and `get_subagent_result` tools,
enabling multi-agent orchestration inside a single Pi session.

No configuration.

### todo

Registers a `todo` tool for the LLM to maintain a persistent todo list across
an agent session. Displayed in the Pi TUI sidebar.

No configuration.

---

## Recommended Third-Party Extensions

These extensions are used by cc-thingz skills or complement the workflow.
Install each with `pi install`.

### pi-powerline-footer

Adds a configurable powerline-style status footer to the Pi TUI.

```bash
pi install npm:pi-powerline-footer
```

No skills depend on this directly, but it improves session readability.

### @tintinweb/pi-subagents

Provides the agent loader that reads agents from `~/.pi/agent/agents/`. Required
for cc-thingz Pi agents to work:

```bash
pi install npm:@tintinweb/pi-subagents
ln -snf \
  ~/.pi/agent/git/github.com/alexei-led/cc-thingz/dist/pi/agents \
  ~/.pi/agent/agents
```

Project-local custom agents are read from `.pi/agents/*.md`. This repo adds
an `advisor` agent in source layout:

- `src/agents/advisor/AGENT.md`
- `src/agents/advisor/pi/frontmatter.yaml`

Compiled artifact: `dist/pi/agents/advisor.md`.

Advisor can use read-only exploration tools (`read`, `grep`, `find`, `ls`,
read-only `bash`) and must avoid file edits.

Expected advisor output:

- `Verdict`
- `Top Risks` (ranked)
- `Next Actions` (ordered, concrete)

Invoke with `Agent({ subagent_type: "advisor", ... })`.

### revdiff

Used by the `reviewing-code` skill for rendering code review diffs in Pi.

```bash
pi install git:github.com/umputun/revdiff
```

### pi-web-providers

Adds web search and research providers to Pi (used by the `researching-web`
skill).

```bash
pi install npm:pi-web-providers
```

### @latentminds/pi-quotas

Tracks token and cost quotas per session. Useful when running long coding
sessions.

```bash
pi install npm:@latentminds/pi-quotas
```

---

## Extension Loading

Pi loads extensions from the directories declared in `package.json`:

```json
"pi": {
  "extensions": ["./dist/pi/extensions"],
  "skills": ["./dist/pi/skills"]
}
```

After `make build`, run `pi install "$(pwd)"` (or `pi install git:github.com/alexei-led/cc-thingz`)
to register the latest build. Run `/reload` in Pi or restart it to pick up changes.

Test files (`*.test.ts`) are excluded from `dist/pi/extensions/` by the build
compiler and are never loaded by Pi.
