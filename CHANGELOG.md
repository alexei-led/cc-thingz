# Changelog

All notable changes to this Claude Code configuration are documented here.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html):
major = breaking config/hook changes, minor = new skills/features, patch = fixes.

## [Unreleased]

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

- **`grill-me`** skill (`dev-tools`): focused decision-tree interview on a single existing plan — one question at a time, recommended answer per question, codebase exploration over questions when answerable. Adapted from [mattpocock/skills](https://github.com/mattpocock/skills) (MIT). See `plugins/dev-tools/skills/grill-me/CREDITS.md`.
- **`improve-codebase-architecture`** skill (`dev-workflow`): surface architectural friction and propose deepening opportunities (shallow → deep modules) using a strict module/interface/seam/adapter/leverage/locality vocabulary. Includes `LANGUAGE.md` glossary, `DEEPENING.md` (4 dependency categories: in-process, local-substitutable, remote-owned, true-external), and `INTERFACE-DESIGN.md` ("Design It Twice" parallel sub-agent pattern). Adapted from [mattpocock/skills](https://github.com/mattpocock/skills) (MIT). See `plugins/dev-workflow/skills/improve-codebase-architecture/CREDITS.md`.

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
