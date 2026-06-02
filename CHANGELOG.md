# Changelog

All notable changes to this Coding Companion suite are documented here.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html):
major = breaking config/hook changes, minor = new skills/features, patch = fixes.

## [Unreleased]

## [5.0.0] - 2026-06-02

### Changed

- Reorganized the installable plugin catalog from eleven source plugins to
  seven coherent plugins: `browser`, `dev-flow`, `discovery`, `git-flow`,
  `infra-ops`, `programming`, and `spec-flow`.
- Renamed `browser-automation` → `browser`, `dev-tools` → `discovery`, and
  `spec-dev` → `spec-flow`, and consolidated `go-dev`, `py-dev`, `ts-dev`,
  and `web-dev` into `programming`.
- Added declarative plugin dependencies in source manifests:
  `browser` → `programming`, `programming` → `dev-flow`, and
  `spec-flow` → `dev-flow`.
- Merged `reviewing-cc-config` into `evolving-config`, keeping config review
  and config-improvement workflows in one skill with review-only and
  apply-fixes modes.
- Clarified `cc-thingz` as “Coding Companion” in the top-level docs and reduced
  Claude-first framing in the README and AGENTS catalog.
- Kept `revdiff-plan-review` as an optional Pi bridge hook and assigned it to
  `spec-flow` instead of leaving it orphaned.

### Removed

- Removed the empty `test-e2e` plugin.
- Removed thin or redundant skills: `analyzing-usage`, `learning-patterns`,
  `mem-history`, `parsing-documents`, and `smart-explore`.
- Removed dead `skill-enforcer` routes for deleted or phantom skills:
  `learning-patterns`, `mem-history`, `reviewing-cc-config`,
  `smart-explore`, `using-gemini`, and `coding`.

### Fixed

- Updated README, AGENTS, contributing docs, release-mirror rewrite rules,
  generated manifests, and hook/test fixtures to match the new plugin layout,
  names, counts, and configuration surface.
- Regenerated all marketplace manifests, plugin outputs, and target-specific
  artifacts for the 5.0.0 layout.

## [4.12.0] - 2026-06-02

### Changed

- Renamed the user-facing browser workflow from `testing-e2e` to
  `browser-automation`, broadened it to rendered UI exploration, validation,
  screenshots, recordings, and browser-flow tests, and made `playwright-skill`
  support-only.
- Slimmed `playwright-skill` from a Playwright tutorial into a runtime-only
  helper reference, fixed dev-server detection, and aligned temporary scripts
  and artifacts under `/tmp/playwright-*`.
- Folded `debating-ideas` into `brainstorming-ideas` and retained the
  challenge protocol as a conditional reference.
- Consolidated Context7 command guidance into `looking-up-docs`, keeping docs
  lookup in one user-facing skill with official-source and web fallback
  references.
- Tightened runtime-neutral instruction wording across several support skills
  and generated targets.
- Plugin and marketplace versions bumped to 4.12.0.

### Removed

- Removed standalone `testing-e2e`, `debating-ideas`, and `context7-cli` skill
  entries after their behavior moved into the replacement skills above.

## [4.11.0] - 2026-06-01

### Fixed

- Pi `ask_user_question` now keeps choices visible for long prompts by wrapping
  and capping question text before rendering options.
- The fix covers both single-select selector prompts and multi-select editor
  prompts, with regression tests for each path.

## [4.10.1] - 2026-06-01

### Changed

- Tightened `writing-go` instructions and Go references for leaner scope,
  version-gated APIs, dependency-aware concurrency guidance, and lowercase
  reference filenames.

## [4.10.0] - 2026-06-01

### Changed

- Tightened `committing-code`, `writing-python`, and `writing-typescript`
  instructions for leaner routing, conditional references, less duplicate
  guidance, and stronger project-first language.
- Stopped auto-routing repo-wide code search and architecture-analysis prompts
  from `skill-enforcer`; companion plugins can own those workflows without
  cc-thingz naming or depending on them.
- Trimmed `reviewing-code` and `refactoring-code` to changed-code review and
  behavior-preserving batch refactors, removing repo-wide architecture/search
  guidance.
- Plugin and marketplace versions bumped to 4.10.0.

### Fixed

- `test-runner` hook: disabled broad project fallback by default and removed
  nearest-Makefile target fallback so focused runs avoid unrelated targets.

### Removed

- Removed unused `watch-team` and `ccgram-messaging` skills, including plugin
  wiring, skill-enforcer routing, generated outputs, and skill eval fixtures.
- Removed `searching-code`; repo-wide code search, AST evidence, codegraph, and
  GitNexus workflows are now outside cc-thingz.
- Removed `improving-codebase-architecture`; architecture review/design/planning
  is now outside cc-thingz.

## [4.9.6] - 2026-05-31

### Fixed

- `test-runner` hook: focused pytest no longer false-fails on support files
  such as `conftest.py`, treats pytest exit code 5 as no-tests success, and
  handles `uv` extras/dependency groups before falling back to local pytest.
- `test-runner` hook: hardened non-Python focused tests — nearest non-root
  Makefile targets now win over broad package fallbacks, Vitest/Jest tolerate
  no related tests, JS helpers under test directories route through related-test
  mapping, full mode can run Vitest/Jest/Bats directly, and failing test
  commands report their real exit code.
- `test-runner` hook: package script detection can use `node` or `bun` when
  `python3` is unavailable or unusable.

## [4.9.5] - 2026-05-29

### Removed

- `docs/skill-format.md` — documented a sidecar model (`SKILL.pi.md`,
  `flat/skills-codex/`) that no longer matches the overlay build;
  `CONTRIBUTING.md` is the accurate authoring reference.
- `scripts/build/migrate_skills.py` and `scripts/build/migrate_hooks.py` —
  one-shot helpers for the completed legacy->`src/` migration, not wired into
  the build or CI. Their tests are dropped; `src/hooks` layout tests remain.

## [4.9.4] - 2026-05-29

### Fixed

- `notify` hook: improved back-navigation in Kitty + tmux — recovers tmux
  client metadata so detection works when `TERM_PROGRAM=tmux` masks the
  terminal, and the click-to-navigate command now chains `open` → kitty
  `focus-tab` → tmux `switch-client` → `select-window` → `select-pane`.
- `notify` hook: less noise — skips `idle_prompt` when the tmux pane is
  already focused (permission prompts still always fire), recovers the real
  `TERM_PROGRAM` from the tmux server env so iTerm/WezTerm under tmux activate
  the right app instead of Terminal.app, and drops the last-commit-subject
  substitution that cluttered idle messages.

## [4.9.3] - 2026-05-28

## [4.9.2] - 2026-05-28

### Changed

- Expanded `reviewing-instructions` to review agent-targeted markdown beyond
  `AGENTS.md` and `CLAUDE.md`, including `body.md`, `references/*.md`, linked
  markdown, and custom prompt/context/rules docs.
- Taught the `reviewing-instructions` linter to discover canonical instruction
  entrypoints, linked support markdown, and heuristic agent-facing instruction
  files while skipping ordinary docs and test fixtures.
- Updated README and skill catalog docs to match the broader
  `reviewing-instructions` scope.

## [4.9.1] - 2026-05-20

### Changed

- GitHub release notes now render from the curated `CHANGELOG.md` section for
  the tag, then append the plugin table and install snippet.
- Made code search skills AST-first by folding ast-grep guidance into
  `searching-code`, keeping `smart-explore` focused on known-file and
  known-symbol extraction, and tightening skill-enforcer routing.

## [4.9.0] - 2026-05-19

### Added

- Added focused hook execution for edited files across lint, format, and tests.
- Added compact linter/test output for AI-agent feedback loops.
- Added project fallback support for package scripts and Makefile targets.

### Changed

- Moved focused tests to agent-stop time and kept post-edit work lint/format-only.
- Updated Python, Go, and JavaScript test commands for faster failure feedback.
- Documented hook controls, fallback order, and exit-code behavior.
- Plugin and marketplace versions bumped to 4.9.0.

## [4.8.3] - 2026-05-18

### Fixed

- Made `smart-lint` compatible with macOS Bash 3.2 so post-edit linting no
  longer false-passes when `mapfile` or associative arrays are unavailable.
- Added regression coverage to keep Bash 4-only constructs out of `smart-lint`.
- Plugin and marketplace versions bumped to 4.8.3.

## [4.8.2] - 2026-05-18

### Changed

- Clarified Python skill guidance for catching multiple exception types: prefer
  parenthesized tuple syntax like `except (KeyError, json.JSONDecodeError) as exc:`
  and avoid Python 3.14-only bare comma syntax.
- Plugin and marketplace versions bumped to 4.8.2.

## [4.8.1] - 2026-05-18

### Changed

- **Plugin renames**: shorter, consistent names across all 9 plugins.
  `dev-workflow` → `dev-flow`, `python-dev` → `py-dev`,
  `typescript-dev` → `ts-dev`, `testing-e2e` → `test-e2e`,
  `spec` → `spec-dev`. The `marketplace_name` override is removed — the
  plugin directory name is now the marketplace display name. cc-forge mirror
  names are unchanged (managed by `MIRROR_NAMES` in `rewrite-mirror.py`).
- Plugin and marketplace versions bumped to 4.8.1.
- README and docs updated to reflect new plugin names.

## [4.8.0] - 2026-05-17

### Changed

- **Agent consolidation (39 → 3)**: collapsed 39 language/domain-specific
  agents into 3 role agents with disjoint enforced capability envelopes —
  `engineer` (Read/Edit/Write/Bash, the sole mutator), `reviewer`
  (Read/Grep/Glob/LS only, provably non-mutating), `advisor` (unchanged;
  ships to Codex, Gemini, and Pi — Claude excluded, it has a built-in
  advisor). Domain procedure and output contracts moved into role-agnostic
  skills; per-language content moved into `references/<lang>.md` inside each
  skill. Routing ambiguity across ~24 indistinct agent keys structurally
  eliminated. See `docs/agent-audit-2026-05-16.md` and the executed plan in
  `docs/plans/completed/`.
- Per-language idioms folded into `writing-<lang>/references/PATTERNS.md`;
  per-language review, test, docs, and architecture content moved into skill
  `references/` directories.
- **Skills consolidation (45 → 43)**: folded `grill-me` into
  `brainstorming-ideas/references/grill-protocol.md` and `spec-core` into
  `spec-status` (orientation + `references/specctl-commands.md`; the bundled
  `specctl.py` relocated and sibling wrappers repointed). Seven heavy skills
  moved ~1,400 inlined lines into conditionally-loaded `references/` files
  (`spec-work`, `spec-plan`, `spec-interview`, `deploying-infra`,
  `using-cloud-cli`, `analyzing-usage`, the four `writing-*`,
  `reviewing-code`, `reviewing-cc-config`). ~6 routing boundaries tightened.
  No capability dropped. See `docs/skills-audit-2026-05-17.md` and the
  executed plan in `docs/plans/`.
- **Gemini CLI agents**: all three role agents now compile to Gemini CLI
  format with a hard `tools:` allowlist in frontmatter; `reviewer` is
  enforced read-only, `advisor` restricted to read + `run_shell_command`.
- **`bun test --isolate`**: each Pi extension test file now runs in a fresh
  module registry, preventing `mock.module` leakage across files on Linux.

### Added

- **`looking-up-docs`** skill: re-split from `context7-cli` as a
  three-tier fallback chain (ctx7 → Perplexity → platform web tools)
  with its own tool permissions.
- **`parsing-documents`** skill: replaces the deleted `pdf-parser` agent with
  vendor-neutral document extraction.

## [4.7.0] - 2026-05-16

### Changed

- **`using-git-worktrees`**: worktrees now live under a single per-project
  root `<project>.worktrees/<branch-slug>` (sibling of the main repo)
  instead of flat `../<project>-<slug>` siblings. The root is derived from
  the main worktree, so create and cleanup work correctly even when
  invoked from inside another worktree, and the root is removed once its
  last worktree is cleaned up.

### Added

- **`using-git-worktrees` PR-merge cleanup**: `scripts/cleanup-worktree.sh`
  removes a worktree and deletes its branch, strict by default — refuses
  unless `gh` confirms the PR is MERGED (`--force` to override). Handles
  the squash/rebase `git branch -d` "not fully merged" trap, `cd`s out of
  the worktree before removing it, runs `git fetch --prune`, and prunes
  the now-empty root.

## [4.6.0] - 2026-05-15

### Added

- **Pi hook-bridge**: synthetic `cc-hooks:invoke` tool exposes CC-style hook
  events to Pi (`Setup`, `PermissionRequest`/`Denied`, `TaskCreated`/`Completed`,
  `TeammateIdle`, `ConfigChange`, `FileChanged`, `WorktreeCreate`/`Remove`,
  `Elicitation`/`Result`). Existing CC hooks run unmodified.
- **`ExitPlanMode` plan-review gate**: routes plan submissions through the
  `revdiff-plan-review` hook (29 min timeout inside a 30 min outer wait), fails
  open when the plugin is absent or upstream raises.
- **Plugin-contributed hooks**: Pi packages can register hooks via the
  `cc-thingz.hooks` field in their `package.json`. Commands are validated:
  must be absolute paths inside the package dir or use `${PKG_DIR}`, and
  shell metacharacters (including `\n`, `\r` to block multi-line smuggling)
  are rejected.
- **Hook progress protocol**: hooks may emit `^^PROGRESS N msg` lines on
  stderr; markers are stripped before stderr reaches the LLM feedback loop.
- **JSONL telemetry**: each hook run appends one line to
  `~/.pi/agent/logs/hooks.log` with event, source, exit code, duration,
  timeout flag, and a 500-byte stderr head. Auto-rotates at 10 MB.
- **`/hooks` UX**: source labels (`bundled` / `global` / `project` / `package`),
  per-hook toggle, and global-scope disable list.
- **`PI_HOOK_TIMEOUT_SEC`**: hooks read the parent's effective timeout and
  self-bound below it so they can exit with a blocking message before SIGKILL.
- **Two-tier timeouts**: synthetic hook callers opt into a non-interactive
  floor so interactive flows keep their longer ceiling.

### Changed

- **Hook-runner modularization**: `hook-runner.ts` split into focused
  sub-modules with a CC anti-corruption layer; `config.ts` further split into
  `config-paths` / `config-parse` / `config-package` / `config-persist` /
  `config-summary` (514 → 175-line facade).
- **`classifyExecResult` extracted** from `runHook` so timeout / overflow /
  numeric-exit branches are unit-testable; `RunHookOptions.onProgress`
  removed (no Pi consumer subscribed).
- **`hooks.json` generated from `meta.yaml`** at build time instead of being
  hand-maintained; build fails loud when a Pi-mapped event is missing from
  `PI_EVENT_ORDER`.
- **`NON_BLOCKING_HOOK_EVENTS` broadened** to cover all post-fact event types
  so a misbehaving hook can't surface stale "denied" results.
- **`HooksConfig.SubagentStop` marked `@deprecated`**: Pi has no native
  subagent-stop runtime event; hooks registered under this key never fire.

### Fixed

- Hook telemetry now records `entry.eventName` (e.g. `PreToolUse`) instead of
  the command path.
- `invokeSyntheticHook` guarded against event-bus teardown after session end.
- Maxbuffer overflow surfaces an explicit cap notice prepended to stderr.
- Hook-bridge: leak in event-handler registration, timeout off-by-one, empty
  `PATH` fallback, and config-change reload debounce.
- `make build` skips `__pycache__` when copying hook support files.

## [4.5.3] - 2026-05-13

### Added

- **`test-runner.sh` multi-ecosystem support**: auto-detects 12 languages (Python,
  JS/TS, Go, Rust, Ruby, Java/Maven, Gradle, .NET, Elixir, PHP, Swift, shell/bats).
  Python uses `uv run pytest` → `.venv/bin/pytest` → `python3 -m pytest` — bare
  `pytest` eliminated to avoid stale shebang wrapper failures.
- **JS framework inference**: detects lockfile-based package manager (bun/pnpm/yarn/npm)
  and infers test framework from config files (`vitest.config.*`, `jest.config.*`,
  `.mocharc.*`) when no `"test"` script exists in `package.json`.
- **Makefile escape hatch in `test-runner.sh`**: checks for `test`, `tests`, `check`,
  or `verify` targets before any language detection — lets projects wire any tool
  without touching the hook. Opt out with `.nomake` file or `SKIP_MAKE=1` env var.
- **`notify.sh` multi-agent support**: agent name detected from JSON payload title,
  `$CLAUDE_CODE_VERSION` env, or "Agent" fallback. Notification group is now
  `${agent_slug}-${session_id}` for proper per-agent separation. Git branch and last
  commit message appended to idle notifications.

### Changed

- README: "Hook Prerequisites" section added with 12-language detection matrix,
  test runner fallback order, linter/formatter, and recommended installs per ecosystem.
- README: Codex and Gemini hook configuration documentation updated.

## [4.5.2] - 2026-05-13

### Fixed

- **Codex hook manifest filename**: renamed `codex.hooks.json` → `hooks.json`;
  Codex discovers plugin hooks via `hooks/hooks.json` by default and ignores
  the `hooks` field in `plugin.json`, so hooks were silently not installed.
  Added `codex_hooks = true` feature flag to `~/.codex/config.toml` (required
  for hooks to fire at runtime).
- **Gemini hook event mappings**: `userpromptsubmit` was mapped to the
  non-existent `UserPromptSubmit` Gemini event; corrected to `BeforeAgent`
  (fires after prompt submission, before planning). `notification` was mapped
  to `None` for Gemini despite Gemini supporting the `Notification` event;
  the `notify` hook is now wired in.

## [4.5.1] - 2026-05-13

### Fixed

- **Hook script casing**: `HOOK.*` → `hook.*` rename now committed to git index;
  macOS case-insensitive filesystem hid the mismatch from CI (Linux is case-sensitive).
- **`rewrite-mirror` workflow**: install `pyyaml` and `uv` before running the script,
  fixing CI failures on cc-forge mirror on every push.

## [4.5.0] - 2026-05-13

### Changed

- **Pi Notification hook consolidated**: `notify.ts` Pi extension removed; `notify.sh`
  is now wired directly in `hook-runner` as a `Notification` event dispatched from
  `agent_end`. All Pi hooks now flow through the shared hook scripts.

## [4.4.0] - 2026-05-13

### Added

- **`file-protector` Codex support**: hook now handles `apply_patch` multi-file
  patches, blocking any patch that touches a protected path and warning on lock files.
  Wired into Codex `PreToolUse` with `^apply_patch$` matcher in
  `codex.hooks.json`.

### Changed

- **`file-protector` rewritten in Python**: replaces the shell script with a
  config-driven Python hook supporting both `file_path` (Claude Code / Gemini) and
  `patch` (Codex) input formats. Config overrides via
  `~/.claude/hook-config.json` — set `protectedPatterns: []` or
  `lockFilePatterns: []` to clear defaults.
- **Hook entry-point naming**: convention changed from `HOOK.*` to `hook.*`;
  build pipeline glob updated accordingly.

### Fixed

- **`_load_patterns` empty-list override**: `protectedPatterns: []` or
  `lockFilePatterns: []` in config now correctly clears the default pattern
  list instead of silently restoring it (was using truthiness instead of
  `is not None`).

### Tests

- Replaced `test_file_protector.bats` with a pytest suite covering single-file,
  `apply_patch` multi-file, malformed input, and config-override cases including
  explicit empty-list clearing.

## [4.3.0] - 2026-05-12

### Fixed

- **Claude Code plugin hooks**: generated per-plugin `hooks/hooks.json` manifests
  for `dev-workflow` and `dev-tools`, so Claude Code installs their hook scripts
  without manual `settings.json` wiring.
- **Release version bumping**: release script now updates project metadata
  (`pyproject.toml`, `package.json`) and Playwright helper package snapshots in
  addition to plugin manifests.

## [4.2.0] - 2026-05-12

### Added

- **`notify.ts` Pi extension**: fires `terminal-notifier` on `agent_end` — mirrors
  `notify.sh` behavior for Claude Code. Displays `[project] Pi` title, activates the
  Kitty terminal tab via `kitten @ focus-tab`, and focuses the tmux pane. Falls back
  silently if `terminal-notifier` is not installed (`brew install terminal-notifier`).
- **`analyzing-usage` expanded to Pi and Codex**: adds `pi/body.md` (ccusage-pi queries
  with `sessionId`/`projectPath` fields) and `codex/body.md` (ccusage-codex queries with
  `costUSD` fields), plus matching reference sheets. Claude-specific content moved to
  `claude/body.md` overlay.
- **`releasing` project skill** (`docs(releasing)`): critical warning against
  `gh release create` with recovery steps; CI creates the release from the pushed tag.

### Fixed

- **Codex marketplace authentication**: `ON_FIRST_USE` → `ON_USE` in
  `.agents/plugins/marketplace.json` — `ON_FIRST_USE` is not a valid Codex value.

### Improved

- **Pi install documentation**: `pi install git:github.com/alexei-led/cc-thingz` is now
  the primary install path for extensions and skills; agents still require a symlink.
  README and CONTRIBUTING updated for all four platforms (Claude Code, Codex, Gemini, Pi).

## [4.1.0] - 2026-05-12

### Added

- **Pi frontmatter overlays for all 38 agents**: each agent now has a `pi/frontmatter.yaml`
  tuning model, thinking level, tool restrictions, and turn limits for the Pi coding agent.
  Model tiers: `openai-codex/gpt-5.5` (engineer/heavy agents), `openai-codex/gpt-5.4`
  (review/docs/planning agents), `openai-codex/gpt-5.4-mini` (scout, pdf-parser).
  Uses provider-qualified model IDs (`openai-codex/` prefix) to avoid fuzzy-match ambiguity
  across azure-openai-responses, github-copilot, minimax-cn, and openai-codex providers.
- **Pi pipeline agents enhanced**: `scout`, `planner`, `reviewer`, `worker` now carry
  explicit `model`, `max_turns`, `thinking`, and (for `worker`) `prompt_mode: append`
  so the agent inherits the parent CLAUDE.md context. Turn budgets: scout 15, planner 20,
  reviewer 30, worker 50.
- **Pi allowlist extended** (`scripts/build/overlay.py`): `max_turns`, `prompt_mode`,
  `memory`, `isolation`, `disallowed_tools` added to the Pi key allowlist so these fields
  are no longer silently dropped when compiling Pi agent output.
- **10 agents made all-platform**: `go-engineer`, `go-simplify`, `infra-engineer`,
  `perplexity-researcher`, `py-simplify`, `python-engineer`, `ts-simplify`,
  `typescript-engineer`, `web-engineer`, `web-simplify` previously had `targets: [claude]`
  or `targets: [claude, pi]`. Targets restriction removed — they now compile for Claude,
  Codex, Gemini, and Pi.
- **`analyzing-usage` skill expanded to Codex and Pi**: targets extended from `[claude]`
  to `[claude, codex, pi]`. Adds `pi/body.md` (ccusage-pi queries, `sessionId` / `projectPath`
  fields), `codex/body.md` (ccusage-codex queries, `costUSD` fields), and matching
  `references/ccusage-pi.md` and `references/ccusage-codex.md` reference sheets.
  Claude-specific content (session profiles, 11 termgraph views) moved to `claude/body.md`
  overlay to prevent leakage into other platforms.

### Improved

- **Agent instruction quality**: 34+ `AGENT.md` files updated — tables converted to bullet
  lists, NOT-guard scope boundaries added, failure-handling sections added, bold pseudo-headers
  converted to real `###` headers.
- **Skill instruction quality**: 9 skill files updated with failure-handling sections, NOT
  guards, and structural fixes.

## [4.0.5] - 2026-05-12

### Added

- **`reviewing-instructions` skill** (replaces `linting-instructions`): model-agnostic instruction
  quality review with 8-dimension scoring (Signal Density, Scope Specificity, Output Structure,
  Format Efficiency, Failure Handling, Grounding Discipline, Routing Precision, Progressive
  Disclosure). Supports `--model` override; looks up model-specific guides from bundled
  `references/models/` (claude, gemini, openai, generic). Bundled linter script
  (`scripts/lint-instructions.py`) moved into the skill; scoring rubric and model-specific
  lint rules (O-prefix, S-prefix) consolidated into `references/` sibling files.
  Multi-target: compiles to all four platforms (claude, codex, gemini, pi).
- **`releasing` project skill** (`.claude/skills/releasing.md`): guided release workflow —
  preflight checks, CHANGELOG update, `scripts/release/release-tag`, and push instructions.

### Removed

- **`linting-instructions` skill** — replaced by `reviewing-instructions`.
  `scripts/validate/lint-instructions.py` moved into the skill bundle.
  `docs/instruction-lint-rules.md` merged into `references/scoring-rubric.md` and
  `references/models/claude.md`.

## [4.0.4] - 2026-05-12

### Fixed

- **Pre-push hook**: auto-commits stale `dist/` artifacts instead of failing hard —
  prevents push blocking when `make build` output wasn't staged before push.
- **CONTRIBUTING.md**: corrected inaccuracies introduced by recent refactors (build paths,
  hook names, script locations).

### Changed

- **Tests**: unified design, eliminated duplication, added coverage configuration across
  all test modules.

## [4.0.3] - 2026-05-12

### Changed

- **`spec` skill** split from monolithic design into 8 hierarchical sub-skills
  (`spec-core`, `spec-init`, `spec-interview`, `spec-plan`, `spec-work`, `spec-status`,
  `spec-done`, `spec-help`) using hyphen-based naming. Trigger patterns and
  skill-enforcer updated accordingly.

### Fixed

- Specctl test path updated after `spec` → `spec-core` rename.
- Golden test fixtures regenerated for playwright-skill and preamble changes.

## [4.0.2] - 2026-05-12

### Changed

- **README and CONTRIBUTING** updated to match current project structure:
  removed references to deleted `docs/skill-compiler-design.md`, removed stale
  root-level `skills`/`hooks` symlinks and `GEMINI.md` from layout docs,
  corrected `dist/pi/` path to include `extensions/`, fixed Gemini hooks path,
  dropped non-existent `using-gemini` skill and `performance-monitor` hook from
  reference tables, removed phantom "9 commands" count from totals.
- **LLM-optimized formatting** applied across all 182 agent and skill instruction
  files: removed horizontal rule separators, converted standalone bold pseudo-headers
  to real `###` headers, stripped low-signal italic markup. Reduces token waste
  without changing instruction semantics.
- **Format lint rules** added (`docs/instruction-lint-rules.md`) and enforced via
  `scripts/validate/lint-instructions.py` (rules: F-NO-TABLE, F-NO-DIAGRAM,
  F-NO-HR, F-NO-ITALIC, F-BOLD-SPARSE).
- **AGENTS.md** consolidated into single project instruction file; `CLAUDE.md`
  now imports it via `@AGENTS.md` to eliminate duplication.

### Removed

- `docs/skill-compiler-design.md` — design is encoded in the compiler source
  and the `CONTRIBUTING.md` layout; the separate design doc was stale.
- Legacy top-level `hooks/`, `agents/`, and `skills/` symlinks removed.

## [4.0.1] - 2026-05-11

### Fixed

- **Marketplace identifier** renamed from `cc-thingz` to `alexei-led-cc-thingz` to match
  the key registered in `settings.json`. Eliminates `/doctor` errors reporting
  "plugin not found in marketplace alexei-led-cc-thingz".
- **Plugin metadata URLs** corrected in all nine plugin manifests — `homepage` and
  `repository` fields now reference the `cc-thingz` repository instead of the old
  `cc-forge` URL.

## [4.0.0] - 2026-05-11

### Added

- **Multi-target skill compiler** (`scripts/build/compile_skills.py`). Single source
  of truth under `src/plugins/*/` compiles to three independent target trees:
  `dist/claude/`, `dist/codex/`, `dist/pi/`. Per-target overlays (e.g.
  `src/plugins/foo/skills/bar/claude/SKILL.md`) merge cleanly over the base without
  polluting other targets.
- **Per-plugin Claude manifests** (`.claude-plugin/plugin.json` in each
  `dist/claude/plugins/<name>/`). Each plugin now ships its own manifest with
  name, version, description, and homepage — enabling per-plugin installs and
  future independent versioning.
- **Codex agent support** — 13 role agents (go-_, py-_, ts-\* impl/docs/tests/idioms/
  simplify/qa + docs-keeper) compiled to `dist/codex/` with Codex-compatible frontmatter
  (drops `model`, renames `effort` → `reasoning_effort`).
- **Pi extension support** — Pi-specific skills and agents compiled to `dist/pi/`
  with smart-home and raspi-cam tooling preserved separately from Claude/Codex targets.
- **Gemini extension improvements** — `gemini-extension.json` regenerated from
  `src/` with consistent structure; `scripts/build/generate_gemini.py` replaces
  the old ad-hoc script.
- **New skills**: `context7-cli` (library docs lookup), `learning-patterns`
  (code pattern extraction), `looking-up-docs` (multi-source doc research).

### Removed

- **Old source paths and scattered generators retired.** The skill compiler
  migration (`docs/plans/completed/20260511-skill-compiler-migration.md`)
  is finished: `plugins/*/skills/`, `plugins/*/agents/`, `plugins/*/commands/`,
  `plugins/*/skills-codex/`, `plugins/*/skills-pi/`, `plugins/*/agents-pi/`,
  `plugins/*/hooks/`, `platforms/pi/`, and `flat/` are gone. The single
  source of truth is now `src/`, and all generated artifacts live under
  `dist/<target>/` plus the three root manifests (`.claude-plugin/marketplace.json`,
  `.agents/plugins/marketplace.json`, `gemini-extension.json`).
- **Deleted generators**: `scripts/build/generate-skills.py`,
  `generate-subagents.py`, `generate-hooks.py`, `generate-agents-md.py`,
  `generate-flat.sh`, `scripts/release/install-pi-exports.sh`, and
  `scripts/_common.py`. `make flat`, `make sync-hooks`, `make generate-hooks`,
  `make overlays`, `make pi-overlays`, `make pi-agents`, `make agents-md`,
  and `make validate-no-plugin-evals` were removed from the Makefile.
- **Obsolete docs**: `docs/pi-skill-export.md` (replaced by README + the
  new design doc `docs/skill-compiler-design.md`).
- **`<!-- CC-ONLY: ... -->` markers** stripped from `src/` content;
  Claude-only artifacts now express intent via base `targets: [claude]` or
  a `claude/` overlay instead of inline markers.
- **`validate-config.py` slimmed down** to validate only the three root
  manifests + `AGENTS.md`; per-source vendor-neutrality is enforced by
  `validate_genericity.py` and golden-file tests in `tests/test_compile_*.py`.

### Changed

- **`scripts/` reorganized** into thematic subdirectories so the three
  audiences are no longer mixed:
  `scripts/build/` (codegen + `_common.py` + `preambles/`),
  `scripts/validate/` (config & instruction linters),
  `scripts/evals/` (paid OpenAI skill-eval workflow),
  `scripts/release/` (`install-pi-exports.sh`, `rewrite-mirror.py`,
  `release-tag`), `scripts/git-hooks/` (versioned commit/push hooks).
  All Makefile targets, CI workflows, docs, tests, and watermarks updated.
  Generated overlays got a one-time watermark refresh.
- **`scripts/build/_common.py`** — extracted shared helpers (`ROOT`,
  `iter_plugin_dirs`, `strip_cc_body`, `remove_empty_dirs`, `sync_files`,
  `DesiredFile`, frontmatter import guard) used by `generate-skills.py`,
  `generate-subagents.py`, `generate-hooks.py`, `generate-agents-md.py`,
  `validate-config.py`. ~180 LOC of duplication removed.
- **`tests/conftest.py`** — adds a `load_script(name)` fixture for new
  tests; replaces ad-hoc `importlib` boilerplate going forward.
- **Shell hygiene** — standardized all shell scripts on
  `#!/usr/bin/env bash`; added `set -uo pipefail` to `notify.sh`
  (previously had no error guard).
- **`session-start` hook** — ported from bash to Python (`session-start.py`).
  Added a proper pytest suite with broader coverage than the prior bats
  smoke test (git context, `.spec/`, `feature_list.json`, project hints,
  malformed stdin).
- **`bq-cost-check`** — ported from bash to Python
  (`bq-cost-check.py`). Replaces brittle `grep -oP` of `bq` text output
  with `bq --format=json` + `json.loads`, and drops the `bc` dependency.
- **Git hooks** — split into `scripts/git-hooks/pre-commit` (fast: lint +
  validate-config + gitleaks staged, ~3 s) and `scripts/git-hooks/pre-push`
  (heavy: drift detection + full test suite). `make setup` now sets
  `core.hooksPath = scripts/git-hooks` so hooks are version-tracked
  instead of copied to `.git/hooks/`.

### Removed

- **`performance-monitor.sh`** — never wired into `hooks.source.yaml` and
  the README's "PostCompact" claim did not match any registered event.

## [2.2.0] - 2026-05-09

### Added

- **`sequential-thinking` skill** (`plugins/dev-tools/skills/sequential-thinking/`).
  Replaces the `sequential-thinking` MCP server with a pure-prompting skill
  that produces numbered Thought blocks with explicit `(revises N)` and
  `Branch X from N` markers, terminating in a `### Final` block. Portable
  across Claude Code, Codex, Gemini, and Pi. Eval at
  `tests/skill-evals/dev-tools/sequential-thinking/` (3 cases including a
  trivial-lookup boundary that confirms the skill correctly does NOT activate).
- **Regression test** `tests/test_no_mcp_sequential_thinking_in_plugins.py`
  blocks `mcp__sequential-thinking__` from re-appearing in source plugins.
- **Skill-enforcer trigger** for the new `sequential-thinking` skill (matches
  "step by step", "sequential thinking", "reason through this", "plan this out",
  "branch this approach", revise-and-branch language).

### Changed

- **Skill-enforcer regex bugfix**: replaced `[\s-]` (literal `\`/`s`/`-` in BSD
  grep) with `[[:space:]-]` so optional whitespace-or-hyphen separators in
  patterns like `up-to-date`, `end-to-end`, `step-by-step`, and `stress-test`
  actually match space variants when `/usr/bin/grep` is used. Affected
  previously-broken triggers: `researching-web`, `testing-e2e`, `grill-me`,
  `debating-ideas`, `improve-codebase-architecture`, `improving-tests`,
  `searching-code`, `refactoring-code`, `learning-patterns`, `evolving-config`,
  `mem-history`, `ccgram-messaging`, `smart-explore`, `spec:work`, `spec:help`,
  `spec:interview`.
- **Agent skills lists** for `python-engineer`, `go-engineer`,
  `typescript-engineer`, `infra-engineer`, `spec-planner`: dropped
  `mcp__sequential-thinking__sequentialthinking` from `tools`/`allowed-tools`,
  added `sequential-thinking` to `skills`, rewrote body refs to invoke the
  skill instead of the MCP tool.
- **`/spec:work` command**: dropped `mcp__sequential-thinking__sequentialthinking`
  from `allowed-tools`.

### Removed

- **`MCP_Sequential.md`** (orphaned root doc that described the now-replaced
  MCP). README integrations table updated to point at the skill.

### Fixed

- **`claude-mem` 13.0.0 `PreToolUse:Read` crash**: the upstream `bun.lock`
  ships without `zod` (which `worker-service.cjs` requires as `zod/v3`). The
  SessionStart patch script (`~/.claude/scripts/patch-claude-mem-async.sh`,
  chezmoi-tracked) now runs `bun install --no-save` for any cached version
  whose `node_modules/zod` is missing — durable across machines, idempotent.

## [2.1.0] - 2026-05-09

### Added

- **Pi TypeScript extensions** (`platforms/pi/extensions/`). 8 extensions that
  mirror Claude-Code-native features in Pi: `smart-lint.ts` (post-edit lint),
  `ask-user-question.ts` (structured ask), `permission-gate.ts` (dangerous bash
  guard), `protected-paths.ts` (blocks writes to `.env`, `.git/`,
  `node_modules/`), `plan-mode/` (`/plan` toggle with step tracking), `todo.ts`
  (`todo` tool + `/todos`, branch-aware state), `subagent/` (single, parallel,
  and chain subprocess spawning), and `structured-output.ts` (terminates the
  agent loop with structured JSON). Deploy via `scripts/install-pi-exports.sh`,
  which now also symlinks `~/.pi/agent/extensions → flat/extensions-pi/`.
- **Gemini CLI hooks** (`hooks/hooks.json`). `BeforeTool` on `write_file|replace`
  → `file-protector.sh`; `BeforeTool` on `run_shell_command` → `git-guardrails.sh`;
  `SessionStart` → `session-start.sh`. All commands resolve via `${extensionPath}`.
- **Codex CLI hooks** (`plugins/dev-workflow/hooks/codex.hooks.json`).
  `PreToolUse` on `Bash` → `git-guardrails.sh`; `SessionStart` → `session-start.sh`.

### Changed

- **Codex hook command paths** switched from `$CLAUDE_PLUGIN_ROOT` to `$PLUGIN_ROOT`.
  `$PLUGIN_ROOT` is the variable Codex injects for plugin-sourced hooks; the old
  `$CLAUDE_PLUGIN_ROOT` alias still works as a compatibility alias but `$PLUGIN_ROOT`
  is now canonical.

## [2.0.0] - 2026-05-09

First-class Pi support, ctx7 CLI replacing context7 MCP, Bun runner coverage,
and an overhauled skill-enforcer hook.

### Added

- **Pi agent exports**. `make pi-overlays` + `make pi-agents` produce
  `flat/skills-pi/` (40 skills: 36 mirrored + 4 Pi-only planning skills) and
  `flat/agents-pi/` (5 subagents: `scout`, `planner`, `reviewer`, `worker`,
  `playwright-tester`). Deploy with `scripts/install-pi-exports.sh --apply`
  (no chezmoi needed) or via the chezmoi recipe in `docs/pi-skill-export.md`.
  Pi requires [`@tintinweb/pi-subagents`](https://github.com/tintinweb/pi-subagents)
  for `Agent` / `get_subagent_result` / `steer_subagent`.
- **Install-script integration tests** (`tests/test_install_pi_exports.py`)
  cover dry-run, apply, idempotency, backup-on-existing, and nested-target
  creation for `scripts/install-pi-exports.sh`.
- **Bun/bunx runner coverage** across all ctx7 and Playwright skills/agents.
  Allowlists now include `Bash(bunx ctx7@latest *)` and `Bash(bunx playwright *)`
  alongside the npx variants. Body examples show both runners; pick by
  lockfile (`bun.lock`/`bun.lockb` → `bunx`, otherwise `npx`).
- **Tool-first / grounding sections** added to web review agents
  (`web-impl`, `web-qa`, `web-tests`, `web-idioms`, `web-simplify`,
  `web-engineer`). Each requires running `html-validate` / `stylelint` /
  `playwright` first and grounding findings in tool output.
- **Skill-enforcer triggers** for `context7-cli`, `grill-me`, and
  `improve-codebase-architecture`; tightened `reviewing-code` and
  `brainstorming-ideas` to exclude overlapping triggers.
- **MCP migration backlog** (`docs/mcp-migration-backlog.md`) tracks remaining
  MCP→CLI work: perplexity-ask, morphllm, deepwiki, claude-mem,
  sequential-thinking.
- **Pi schedules placeholder** (`.pi/subagent-schedules/README.md`) reserved
  for future cron-style schedules; not deployed by `install-pi-exports.sh`.

### Changed

- **context7 MCP removed from source agents and skills**. 11 Claude Code
  agents (`go-engineer`, `python-engineer`, `typescript-engineer`,
  `infra-engineer`, `web-engineer`, `playwright-tester`, `docs-keeper`, and
  the four `*-simplify` review agents) plus 2 skills (`exploring-repos`,
  `documenting-code`) now invoke `ctx7` via `Bash(ctx7 *)` /
  `Bash(npx ctx7@latest *)` / `Bash(bunx ctx7@latest *)`. Body references
  rewritten to use `ctx7 library` / `ctx7 docs`. Locked by
  `tests/test_no_mcp_context7_in_plugins.py`.
- **Skill instructions strengthened for ctx7 emission**. `context7-cli` and
  `looking-up-docs` now require the response to SHOW the actual `ctx7`
  commands invoked — claiming "I used Context7" without an emitted command
  no longer satisfies the workflow.

### Docs

- **README install rewrite** assumes no chezmoi by default. Each section
  states its CLI prerequisite, links upstream installers, and shows the
  exact symlink targets / settings.json snippets for Codex, Gemini, and Pi.
- **`docs/pi-skill-export.md`** cross-links to `.pi/subagent-schedules/README.md`
  and `docs/mcp-migration-backlog.md`; smoke-check list updated for the new
  `playwright-tester` Pi agent.

### Migration notes

- **Claude Code users**: no action needed. Agents that previously used
  `mcp__context7__*` now use the `ctx7` CLI directly. If `ctx7` is not
  installed, agents fall back to `npx ctx7@latest` / `bunx ctx7@latest`.
- **Codex / Gemini users**: the overlay pipeline already stripped MCP
  references, so behavior is unchanged. Newly added `Bash(bunx …)`
  allowlist entries are pure additions.
- **Pi users (new)**: install `@tintinweb/pi-subagents` then run
  `scripts/install-pi-exports.sh --apply`. See README "Pi" section.

## [1.10.1] - 2026-05-08

### Fixed

- **CI workflow startup**: moved skill-eval workspace configuration out of the invalid `runner.temp` job-level context so GitHub Actions can start CI jobs.

## [1.10.0] - 2026-05-08

### Added

- **Skill eval automation**: added deterministic unit coverage for skill-eval preparation, summaries, Gemini context generation, and export validation.
- **Gemini context generation**: new `scripts/generate-gemini-md.py` plus `make gemini-md` / `validate-gemini-md` keep `GEMINI.md` generated from `flat/skills-codex/`.
- **Fast skill eval workflows**: `SKILL_EVAL_BASELINE`, `SKILL_EVAL_HTML_REPORT`, `skill-evals-fast`, and `skill-evals-both` speed up local iteration and source-vs-overlay checks.

### Changed

- **Skill quality pass**: tightened eval-driven instructions across development workflow, dev-tools, infra, Python, web, and E2E skills; regenerated Codex/Gemini overlays.
- **Skill export hygiene**: validation now catches stale/missing Gemini skill links, stale Gemini skill counts, and Claude-only tool leaks in Codex/Gemini overlays.
- **Docs**: refreshed README, CONTRIBUTING, skill eval docs, `AGENTS.md`, and `GEMINI.md` for 35 exported skills and the new eval workflows.

### Fixed

- **Gemini drift**: `GEMINI.md` now includes all 35 flat Codex/Gemini skills and the root Gemini extension version/count is current.
- **Overlay portability**: stripped Claude-specific MCP/tool names from generated Codex/Gemini skill overlays.

## [1.9.1] - 2026-05-03

### Added

- **Architecture-tier linting** in `smart-lint.sh` (`dev-workflow`): wires `knip` (unused exports / files / deps) and `dependency-cruiser` (boundary rules and import cycles) for TypeScript / JavaScript projects. Both opt-in by their own config-file presence (`knip.json`, `.dependency-cruiser.cjs`, etc.) — no env var to enable. Falls back through `bunx` and `npx` when the binary isn't on `PATH`; emits a stdout install hint (does not block) when no runner is available.
- **Layered hook config** in `smart-lint.sh`: sources `~/.claude/.claude-hooks-config.sh` (global defaults) then `./.claude-hooks-config.sh` (project overrides) so per-project settings override per-user defaults. Per-tool linters keep reading their own project configs (`.golangci.yml`, `pyproject.toml`, `.prettierrc`, `knip.json`, `.dependency-cruiser.cjs`).
- **`SKIP_ARCH=1` env var and `.nolint-arch` marker file** to skip just the architecture tier without disabling fast-tier linters. Existing `SKIP_LINT=1` and `.nolint` continue to skip everything.
- **`plugins/dev-workflow/docs/lint-tools.md`**: new reference doc with install commands (brew / uv / bun) for every tool the hook touches, architecture-tier opt-in instructions, skip recipes, and a pointer to `.golangci.yml` for Go architecture enforcement (`depguard`, `gomodguard`, `cyclop`, `revive`).

### Fixed

- `lint_shell()` now skips `.claude-hooks-config.sh` files. They are sourced (not executed) and routinely written without shebangs, so shellcheck's `SC2148` was incorrectly blocking edits when a project added per-project hook config.

## [1.9.0] - 2026-05-03

### Added

- **`grill-me`** skill (`dev-tools`): focused decision-tree interview on a single existing plan — one question at a time, recommended answer per question, codebase exploration over questions when answerable.
- **`improve-codebase-architecture`** skill (`dev-workflow`): surface architectural friction and propose deepening opportunities (shallow → deep modules) using a strict module/interface/seam/adapter/leverage/locality vocabulary. Includes `LANGUAGE.md` glossary, `DEEPENING.md` (4 dependency categories: in-process, local-substitutable, remote-owned, true-external), and `INTERFACE-DESIGN.md` ("Design It Twice" parallel sub-agent pattern).

### Changed

- **`brainstorming-ideas`** description: routes pure "grill me" requests on a single plan to the new `grill-me` skill; brainstorming-ideas remains the broader brainstorm/design/grill flow.

## [1.8.0] - 2026-04-30

### Added

- **Git guardrails**: new `git-guardrails.sh` hook blocks destructive git commands such as hard resets, force pushes, branch deletion, destructive checkout/restore, and forced cleans while allowing normal push workflows.

### Changed

- **Workflow skills**: enriched existing skills with diagnosis, TDD, test quality, architecture review, domain vocabulary, and zoom-out guidance instead of adding overlapping new skills.
- **`brainstorming-ideas`**: clarified that it brainstorms ideas and stress-tests draft plans before coding; implementation task breakdown remains `/spec:plan`.
- **Spec commands**: simplified planning around vertical slices, blockers/open questions, out-of-scope checks, and durable completion evidence; removed noisy task taxonomy and stale evidence flags.
- **Skill routing**: updated `skill-enforcer.sh` triggers for debugging, TDD, plan grilling, domain terms, zoom-out search, and architecture review without duplicating intent across skills.
- **Instruction quality checks**: expanded the advisory linter with rules for clear names, trigger-rich descriptions, progressive disclosure, and sequential user questions.
- **Docs and exports**: refreshed README/plugin counts, AGENTS.md, flat symlinks, and Codex/Gemini skill overlays for 33 skills, 34 agents, 10 hooks, and 9 commands.

### Fixed

- **Spec completion docs**: removed references to unsupported `specctl done --evidence` usage and aligned examples with the actual CLI flags.

## [1.9.1] - 2026-05-03

## [1.7.1] - 2026-04-19

### Changed

- **`reviewing-code` skill**: replaced unscoped `Bash` with scoped permissions (`Bash(git *)`, `Bash(gh pr *)`, `Bash(gh api *)`, `Bash(rg *)`, `Bash(wc *)`); added `Read`/`Grep`/`Glob`/`LS`/`LSP` for fallback inspection of user-provided file paths
- **24 review sub-agents** (`go-*`, `py-*`, `ts-*`, `web-*` × `qa/impl/tests/idioms/docs/simplify`): scoped unscoped `Bash` to per-language read-only tooling. Top-level engineers (`go-engineer`, `python-engineer`, `typescript-engineer`, `web-engineer`) untouched
- **`writing-python` skill**: expanded "Verify Generated Code" with explicit retry loop (`ruff --fix` → format → `pyright` → repeat until green)
- **`testing-e2e` skill**: expanded Phase 3 with pass criteria, retry steps, and full-suite regression run
- **8 skills**: `TodoWrite` → `TaskCreate` / `TaskUpdate` / `TaskList` in frontmatter and prose. Per CC spec, `TodoWrite` is non-interactive/SDK only; interactive sessions use `Task*`
- **`linting-instructions` skill**: model `opus` → `sonnet` (rule-based regex linting doesn't need Opus reasoning)
- **`looking-up-docs` skill**: removed dead `WebSearch` and `mcp__perplexity-ask__perplexity_ask` (description explicitly excludes general web search)

### Fixed

- **`mem-history` skill**: added `context: fork` — `get_observations` returns 500–2k tokens per result and was leaking into the main context

### Notes

- All 9 plugins bumped to 1.7.1 to align with marketplace tag
- PR #6 (yogesh-tessl) closed without merge: the "frontmatter validation fix" was based on a third-party Tessl validator, not the Claude Code spec — which explicitly accepts both YAML lists and space-separated strings for `allowed-tools`. Useful prose changes (verify loops) cherry-picked manually

## [1.9.1] - 2026-05-03

## [1.7.0] - 2026-04-17

### Added

- **Private mirror support**: `scripts/rewrite-mirror.py` rewrites plugin manifests (repository URLs, homepage links, plugin names) for private GitHub mirrors — configurable per-mirror name maps in `MIRROR_NAMES`
- **Mirror sync workflow**: `.github/workflows/rewrite-mirror.yml` auto-rewrites manifests on push to mirror repos; condition-gated on `github.repository` to skip the source repo; commits with `[skip ci]` to prevent trigger loops

### Changed

- **Plugin manifests**: All `plugin.json` and `marketplace.json` files enriched with full metadata — `author.email`, `author.url`, `homepage` URLs, expanded `keywords` arrays across all 9 plugins
- **`make push`**: Simplified to plain dual-push (`origin` + mirror remotes); CI on mirror repos handles manifest rewrites automatically

## [1.9.1] - 2026-05-03

## [1.6.3] - 2026-04-16

### Added

- **`coding` skill**: Language-agnostic process discipline for all implementation tasks — surfaces assumptions before coding, defines verifiable success criteria first. Complements writing-go/python/typescript/web with process guardrails. Auto-activates on implement/write/create/build/add/develop intent; wired into go-engineer, python-engineer, typescript-engineer, web-engineer agents.
- **`smart-lint.sh` skip gate**: Skip auto-linting via `SKIP_LINT=1 <command>` (transient) or `.nolint` file in project root (persistent, add to `.gitignore`). Useful when editing repos you don't own and want to avoid auto-formatting side-effects.

## [1.9.1] - 2026-05-03

## [1.6.2] - 2026-04-12

### Fixed

- **test-runner.sh**: Exit 0 (informational) instead of exit 2 (blocking) when no test framework found — prevents spurious "Claude must fix" errors for unknown project types, missing pytest, or missing cargo
- **smart-explore**: Added `context: fork` — file-reading fallback now runs in isolated context
- **documenting-code**: Phase 5 independently verifies changes via `git diff --stat` instead of trusting agent self-report
- **reviewing-cc-config**: Slimmed from 447→237 lines (−47%); agents read RUBRIC.md directly instead of inline rules; added cross-check step; RUBRIC.md now required (no silent fallback)
- **exploring-repos**: Removed unused Read/Grep/Glob from `allowed-tools`

### Changed

- **Model routing** (per Anthropic system cards): `go-impl`, `go-qa`, `py-impl`, `py-qa`, `ts-impl`, `ts-qa` downgraded opus→sonnet (checklist review, 3–5× cost reduction); `go-docs`, `py-docs`, `ts-docs`, `web-docs` upgraded haiku→sonnet (semantic doc quality)
- **Skill descriptions**: Added trigger phrases and NOT-for exclusions to `looking-up-docs`, `researching-web`, `writing-web`, `reviewing-code` for cleaner routing
- **skill-enforcer.sh**: Added negative patterns for 3 overlapping pairs (code/config review, docs/research, web/typescript) — all disambiguation tests pass

## [1.9.1] - 2026-05-03

## [1.6.0] - 2026-04-07

### Added

- **`reviewing-cc-config` skill**: Review Claude Code configuration (skills, agents, hooks, CLAUDE.md, commands) for context efficiency, signal density, and anti-patterns — derived from Anthropic's "Effective Context Engineering for AI Agents" and Claude Code best practices documentation
- Co-located `RUBRIC.md` with 16 review rules across 4 categories: Context Budget (CB-\*), Signal Density (SD-\*), Architecture (AR-\*), Anti-Patterns (AP-\*)
- Spawns up to 4 parallel review agents per component type with token-capped structured output
- Skill-enforcer trigger patterns for "review config", "config review", "context review", "review skills/agents/hooks"
- Skill count: 31 → 32 (dev-tools: 14 → 15)

## [1.9.1] - 2026-05-03

## [1.5.0] - 2026-04-03

New skill: explore public GitHub repositories via DeepWiki AI-generated documentation.

### Added

- **`exploring-repos` skill**: AI-powered exploration of 30,000+ public GitHub repositories via DeepWiki MCP — understand architecture, design patterns, component relationships, and cross-repo comparisons without cloning
- Three DeepWiki MCP tools: `read_wiki_structure` (topic index), `read_wiki_contents` (full wiki), `ask_question` (semantic Q&A with multi-repo support)
- GitHub CLI (`gh`) fallback strategy for repos not indexed by DeepWiki — `gh repo view`, `gh api`, `gh search code` work for any public repo
- Tiered fallback chain: DeepWiki → GitHub CLI → Context7 → Perplexity → local clone
- Clear DeepWiki vs Context7 decision table (architecture understanding vs API references)
- Skill-enforcer trigger patterns for "explore repo", "deepwiki", "repo architecture", "how does owner/repo work"

## [1.9.1] - 2026-05-03

## [1.4.0] - 2026-04-02

AGENTS.md adoption and CC-first rebrand.

### Added

- **AGENTS.md generation**: `scripts/generate-agents-md.py` builds `AGENTS.md` from `flat/skills-codex/` with categorized skill tables — compatible with 20+ AI coding tools via the Linux Foundation AGENTS.md standard
- `make agents-md` and `make validate-agents-md` targets
- AGENTS.md badge in README
- Installation section for AGENTS.md-compatible tools (GitHub Copilot, Cursor, Windsurf, Devin)
- Tests for AGENTS.md generator (16 tests)

### Changed

- **Rebranded** from "cross-platform collection" to "Claude Code plugin suite with portable skill export"
- README tagline, badges, section headers, and Platform Support table updated to CC-first framing
- "Cross-Platform Architecture" section renamed to "Skill Export Architecture"
- Codex/Gemini badges changed from "compatible" to "skill_export"
- `.claude-plugin/marketplace.json` description updated
- `gemini-extension.json` description updated

### Fixed

- GEMINI.md skill drift: added 6 missing skills (`evolving-config`, `learning-patterns`, `linting-instructions`, `mem-history`, `smart-explore`, `using-gemini`) — now lists all 29 skills

## [1.9.1] - 2026-05-03

## [1.3.0] - 2026-04-02

Cross-platform plugin support for OpenAI Codex CLI and Google Gemini CLI.

### Added

- **Codex CLI support**: `.codex-plugin/plugin.json` manifests for all 9 plugins, `.agents/plugins/marketplace.json` Codex marketplace
- **Gemini CLI support**: `gemini-extension.json` at repo root and per-plugin, `GEMINI.md` context file, `skills/` symlink for Gemini skill discovery
- **Platform-aware skill overlay system** (`scripts/generate-overlays.py`):
  - Three-tier skill classification: GREEN (15 shared), YELLOW (8 auto-stripped), RED (6 hand-authored)
  - CC-specific frontmatter stripping for all non-Claude platforms
  - `<!-- CC-ONLY: begin/end -->` body sentinel markers for section stripping
  - Platform preamble injection with agentic anchors for o3/codex-1 and Gemini models
- 6 hand-crafted `SKILL.codex.md` overlays optimized for o3/codex-1 instruction following: reviewing-code, fixing-code, improving-tests, brainstorming-ideas, deploying-infra, testing-e2e
- `skills-codex/` build output directories in all 9 plugins (29 platform-optimized skills)
- `flat/skills-codex/` symlinks for cross-tool access
- `make overlays` and `make validate-overlays` targets
- Codex CLI and Gemini CLI badges in README
- Installation guides for all 3 platforms in README
- Multi-platform manifest templates in CONTRIBUTING

### Fixed

- smart-lint.sh: skip symlinks in markdown formatting (prettier errors on symlinked .md files)
- CI: run overlay build before validation to handle cross-Python serialization
- CC plugin versions synced from 1.2.0 to 1.2.2

### Changed

- All 9 `.codex-plugin/plugin.json` skills pointer: `./skills/` → `./skills-codex/`
- Codex and Gemini get platform-optimized skills instead of CC source
- README structure diagram expanded to show dual-manifest layout
- CONTRIBUTING directory structure shows all 3 platform manifests

## [1.9.1] - 2026-05-03

## [1.2.2] - 2026-04-01

Documentation accuracy fixes for README.

### Fixed

- Agent model table: engineers were listed as opus but are actually sonnet
- Add 4 missing skills to user-invocable table (analyzing-usage, learning-patterns, linting-instructions, using-git-worktrees)
- Move learning-patterns and using-git-worktrees from auto-activated to user-invocable
- Add playwright-skill to auto-activated table, pdf-parser to agents table
- Update dev-tools skill count: 13 → 14
- Narrow linting-instructions enforcer triggers to skill/agent authoring context
- Clarify linting-instructions description: references Anthropic model cards

## [1.9.1] - 2026-05-03

## [1.2.1] - 2026-04-01

System card-derived instruction hardening for all agents and skills.

### Added

- `linting-instructions` skill: model-based prompt review against system card rules
- `scripts/lint-instructions.py`: advisory regex linter with uv inline deps
- `docs/instruction-lint-rules.md`: 12 rules (6 universal, 3 opus, 3 sonnet) with citations
- `make lint-instructions` target (advisory, doesn't fail CI)
- Skill-enforcer trigger for linting-instructions

### Fixed

- Opus agents (6): add efficiency constraints, tool failure handling, grounding, read-only clauses
- Sonnet agents (24): add anti-eagerness clauses, scope locks for review agents
- `infra-engineer`: add destructive action safety for cloud CLI commands
- `docs-keeper`: add write scope ceiling for Edit/Write/MultiEdit tools
- `web-engineer`: add scope boundaries, failure handling, workflow structure
- `web-docs`: add "Run Tooling First" section (was only doc agent missing it)
- `managing-infra`: add mandatory dry-run before terraform/kubectl/helm apply
- Writing skills (4): add verify-after-generate with build/lint commands
- `committing-code`: add secrets detection guard for .env/pem/credentials
- `documenting-code`, `improving-tests`, `debating-ideas`: add failure handling
- `mem-history`: add scope description and output format template

### Changed

- Skill count: 29 → 30 (new linting-instructions in dev-tools)
- All instruction fixes derived from Claude Opus 4.6 and Sonnet 4.6 system cards

## [1.9.1] - 2026-05-03

## [1.2.0] - 2026-03-31

Optional claude-mem integration for AST-based code navigation and cross-session memory.

### Added

- `smart-explore` skill: AST-based code navigation via smart_outline/smart_search/smart_unfold (10-20x token savings)
- `mem-history` skill: cross-session memory search with 3-layer workflow and graceful fallback
- Claude-mem MCP tools added to all 30 agents (25 review + 5 engineer) as optional tools
- Historical context check in `reviewing-code` (Step 0) and `fixing-code` (Pre-Phase 2)
- Project history option in `brainstorming-ideas` Phase 3 checkpoint
- Smart Explore column in `searching-code` decision table
- `smart-explore` and `mem-history` detection patterns in skill-enforcer hook
- Claude-Mem Integration section in README with installation guide and resilience docs

### Changed

- Skill count: 27 → 29 (2 new skills in dev-tools plugin)
- All review agent frontmatter converted to multi-line tools format
- Engineer agents gain `### Memory (claude-mem)` body section

## [1.9.1] - 2026-05-03

## [1.1.1] - 2026-03-31

Full repository review and cleanup.

### Fixed

- Broken specctl test path after plugin restructuring (10 test failures)
- Ruff config referencing deleted `scripts/ce` (linter was scanning nothing)
- Plugin version mismatch (all plugin.json now match marketplace 1.1.1)
- Skill-enforcer missing 4 user-invocable skills
- `learning-patterns` skill name mismatch (was `learn`, now matches directory)
- CI gate not detecting cancelled job state
- README skill counts (26 → 27)

### Added

- Per-plugin README.md for all 9 plugins
- Makefile with lint, test, validate, fmt, flat, ci, setup, release targets
- CONTRIBUTING.md with plugin authoring guide and PR checklist
- Pre-commit hook running full CI pipeline
- Release tag script with automatic version bumping
- CI badge, version badge, and project narrative in README
- Dependabot pip ecosystem tracking
- `using-gemini` skill documented in README

### Changed

- Replaced monolithic GUIDE.md with per-plugin READMEs + expanded project README
- CI and release workflows now use Makefile targets
- All lint/test jobs run unconditionally on push to master
- Dependabot frequency: monthly → weekly

### Removed

- GUIDE.md (split into per-plugin READMEs)
- Orphaned root files: claude-powerline.json, MCP_Sequential.md, .claude-hooks-config.sh, .claude-hooks-ignore
- install-tools.sh (user-specific, not marketplace-related)

## [1.9.1] - 2026-05-03

## [1.1.0] - 2026-03-30

Restructured as a 9-plugin marketplace for community sharing.

### Added

- MIT LICENSE file
- Marketplace metadata (description, version, categories, tags)
- Plugin-level `plugin.json` manifests for all 9 plugins

### Changed

- Restructured from flat config into 9 installable plugins
- 26 skills, 34 agents, 9 hooks, 9 commands across all plugins
- Updated README with correct installation syntax per official plugin docs
- Updated GUIDE with plugin-relative paths and companion tool notes

## [1.9.1] - 2026-05-03

## [1.0.0] - 2026-02-28

Initial versioned release of the Claude Code configuration.

### Added

- 23 skills: brainstorming, committing, debating, deploying-infra, documenting,
  evolving-config, fixing, improving-tests, learning-patterns, looking-up-docs,
  managing-infra, refactoring, researching-web, reviewing, searching,
  testing-e2e, using-cloud-cli, using-git-worktrees, using-modern-cli,
  writing-go, writing-python, writing-typescript, writing-web
- 14 agents for Go, Python, TypeScript, web, infrastructure, and planning
- Spec-driven development system (specctl + spec skills)
- CI workflow with config validation, linting, and tests
- Global CLAUDE.md with universal development practices
- Project CLAUDE.md with config-repo-specific guidance
- Git hooks: gitleaks pre-commit, enforcer post-tool-use
