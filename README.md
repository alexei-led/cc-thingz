# cc-thingz

[![CI](https://github.com/alexei-led/cc-thingz/actions/workflows/ci.yml/badge.svg)](https://github.com/alexei-led/cc-thingz/actions/workflows/ci.yml)
[![GitHub tag](https://img.shields.io/github/v/tag/alexei-led/cc-thingz?label=version&sort=semver)](https://github.com/alexei-led/cc-thingz/tags)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Claude Code](https://img.shields.io/badge/Claude_Code-plugin_marketplace-blueviolet)](https://docs.anthropic.com/en/docs/claude-code)
[![AGENTS.md](https://img.shields.io/badge/AGENTS.md-standard-000000)](https://agents.md)
[![Codex CLI](https://img.shields.io/badge/Codex_CLI-skill_export-10A37F)](https://developers.openai.com/codex/plugins)
[![Gemini CLI](https://img.shields.io/badge/Gemini_CLI-skill_export-4285F4)](https://geminicli.com/docs/extensions)
[![Plugins](https://img.shields.io/badge/plugins-9-green)](plugins/)
[![Skills](https://img.shields.io/badge/skills-33-green)](plugins/)

A **Claude Code** plugin suite — 33 skills, 34 agents, 10 hooks, and 9 commands — with portable skill export for Codex CLI, Gemini CLI, and [AGENTS.md](https://agents.md)-compatible tools. Built over 6+ months of daily use and continuous refinement.

Built for Claude Code, with all 33 skills exported as platform-optimized instructions for Codex CLI, Gemini CLI, and any tool supporting the AGENTS.md standard.

## Why This Exists

AI coding tools are powerful out of the box, but specialized workflows need specialized prompts. After months of iterating on skills, agents, and hooks across Go, Python, TypeScript, infrastructure, and planning workflows, these plugins encode hard-won patterns:

- **Code review** with parallel multi-agent review and sequential lint-and-check workflows
- **Smart hooks** that auto-suggest skills, lint after edits, protect secrets, and run tests (Claude Code)
- **Spec-driven development** with structured requirements, tasks, and a CLI for project management
- **Infrastructure ops** with validated K8s, Terraform, and Helm deployments
- **Developer utilities** including worktree isolation, codebase search, web research, and brainstorming

Every skill has been manually crafted and refined through real-world use — not generated boilerplate.

## Installation

### Claude Code

```bash
/plugin marketplace add alexei-led/cc-thingz
/plugin install dev-workflow@cc-thingz
/plugin install go-dev@cc-thingz
```

Use `--scope project` to install into `.claude/settings.json` for team sharing.

### OpenAI Codex CLI

```bash
git clone https://github.com/alexei-led/cc-thingz.git
# Codex discovers plugins via .agents/plugins/marketplace.json
codex plugin list
codex plugin install go-dev
```

### Google Gemini CLI

```bash
gemini extensions install https://github.com/alexei-led/cc-thingz
```

Individual plugins can also be installed as standalone extensions:

```bash
gemini extensions install --path=./plugins/go-dev
```

### Other AGENTS.md-Compatible Tools

The `AGENTS.md` at the repo root provides a skill catalog readable by any tool supporting the [AGENTS.md standard](https://agents.md) (GitHub Copilot, Cursor, Windsurf, Devin, and others).

## Prerequisites

Some plugins use MCP servers for enhanced capabilities. These are optional — plugins degrade gracefully without them.

| MCP Server                                                                                              | Purpose                                     | Used By                                                                  |
| ------------------------------------------------------------------------------------------------------- | ------------------------------------------- | ------------------------------------------------------------------------ |
| [Context7](https://github.com/upstash/context7)                                                         | Library and framework documentation lookup  | All 9 plugins                                                            |
| [DeepWiki](https://cognition.ai/blog/deepwiki-mcp-server)                                               | AI-generated wiki for public GitHub repos   | dev-tools                                                                |
| [Perplexity](https://github.com/ppl-ai/modelcontextprotocol)                                            | Web research and technical comparisons      | dev-workflow, dev-tools, infra-ops                                       |
| [Sequential Thinking](https://github.com/modelcontextprotocol/servers/tree/main/src/sequentialthinking) | Step-by-step reasoning for complex planning | go-dev, python-dev, typescript-dev, infra-ops, spec-system               |
| [MorphLLM](https://github.com/morphllm/morph-claude-code)                                               | Fast codebase search and batch file editing | dev-workflow, go-dev, python-dev, typescript-dev, infra-ops, spec-system |

### Claude-Mem Integration

All agents and several skills optionally integrate with [claude-mem](https://github.com/thedotmack/claude-mem) for cross-session memory and AST-based code navigation. Install with:

```bash
/plugin marketplace add thedotmack/claude-mem
/plugin install claude-mem@thedotmack
```

**What this enables:**

| Capability                    | Tools Used                                      | Benefit                                            |
| ----------------------------- | ----------------------------------------------- | -------------------------------------------------- |
| AST code navigation           | `smart_search`, `smart_outline`, `smart_unfold` | 10-20x fewer tokens than reading full files        |
| Cross-session memory          | `search`, `get_observations`, `timeline`        | Find past decisions, known gotchas, recurring bugs |
| Historical context in reviews | `search` + `get_observations`                   | Review agents check past findings before starting  |

**Graceful degradation**: All plugins work without claude-mem. When it's not installed, MCP tools are silently absent — agents fall back to Read/Grep/Glob, and skills skip history checks. No errors, no configuration needed.

**How it works**: Agent frontmatter lists claude-mem MCP tools alongside standard tools. Claude Code silently omits unavailable tools at runtime, so agents always have their core tools (Read, Grep, Glob, LSP) and gain smart_explore/memory tools when claude-mem is present. Skill instructions use "when available" / "if claude-mem available" phrasing to guide Claude's behavior.

## Plugins

| Plugin                                                 | Skills | Agents | Description                                                                        |
| ------------------------------------------------------ | ------ | ------ | ---------------------------------------------------------------------------------- |
| [**dev-workflow**](plugins/dev-workflow/README.md)     | 9      | 25     | Code review, fixes, commits, linting hooks, and 24 language-specific review agents |
| [**go-dev**](plugins/go-dev/README.md)                 | 1      | 1      | Idiomatic Go development with stdlib-first patterns, testing, and CLI tooling      |
| [**python-dev**](plugins/python-dev/README.md)         | 1      | 1      | Python 3.12+ development with uv/ruff/pyright toolchain                            |
| [**typescript-dev**](plugins/typescript-dev/README.md) | 1      | 1      | TypeScript with strict typing, React patterns, and modern tooling                  |
| [**web-dev**](plugins/web-dev/README.md)               | 1      | 1      | Web frontend with vanilla HTML, CSS, JavaScript, and HTMX                          |
| [**infra-ops**](plugins/infra-ops/README.md)           | 3      | 1      | Kubernetes, Terraform, Helm, GitHub Actions, AWS, GCP                              |
| [**dev-tools**](plugins/dev-tools/README.md)           | 15     | 2      | Modern CLI, git worktrees, docs lookup, web research, config review, brainstorming |
| [**spec-system**](plugins/spec-system/README.md)       | 0      | 1      | Spec-driven development: requirements, tasks, and planning workflows               |
| [**testing-e2e**](plugins/testing-e2e/README.md)       | 2      | 1      | E2E testing with Playwright: browser automation and test generation                |

**Totals**: 33 skills, 34 agents, 10 hooks, 9 commands

## Skills

Skills teach the AI model domain-specific knowledge and workflows. All skills are authored for Claude Code and exported with platform-optimized instructions for Codex CLI, Gemini CLI, and [AGENTS.md](https://agents.md)-compatible tools. On Claude Code, the `skill-enforcer` hook auto-suggests relevant skills based on your prompt.

### User-Invocable

Invoke as `/skill-name` or let the skill enforcer suggest them.

| Skill                  | What It Does                                      | Example Trigger                      |
| ---------------------- | ------------------------------------------------- | ------------------------------------ |
| `brainstorming-ideas`  | Brainstorm ideas and stress-test draft plans      | "brainstorm", "grill plan"           |
| `committing-code`      | Smart git commits with logical grouping           | "commit", "save changes"             |
| `debating-ideas`       | Dialectic agents stress-test design decisions     | "debate", "pros and cons"            |
| `deploying-infra`      | Validate + deploy K8s/Terraform/Helm              | "deploy to staging", "rollout"       |
| `documenting-code`     | Update docs based on recent changes               | "update docs", "document"            |
| `evolving-config`      | Audit config against latest Claude Code features  | "evolve", "audit config"             |
| `exploring-repos`      | Explore GitHub repos via DeepWiki AI wiki         | "explore repo", "deepwiki"           |
| `fixing-code`          | Parallel agents fix all issues, zero tolerance    | "fix errors", "make it pass"         |
| `improving-tests`      | Refactor tests: combine to tabular, fill gaps     | "improve tests", "coverage"          |
| `looking-up-docs`      | Library documentation via Context7                | "look up docs", "API ref"            |
| `mem-history`          | Query past sessions and decisions (claude-mem)    | "last session", "what happened"      |
| `researching-web`      | Web research via Perplexity AI                    | "research", "X vs Y"                 |
| `reviewing-code`       | Multi-agent review (security, quality, idioms)    | "review code", "check this"          |
| `testing-e2e`          | Playwright browser automation and test gen        | "e2e test", "playwright"             |
| `analyzing-usage`      | Analyze Claude Code usage, cost, and efficiency   | "usage", "cost", "spending"          |
| `learning-patterns`    | Extract learnings and generate customizations     | "learn", "extract learnings"         |
| `linting-instructions` | Lint plugin prompts against Anthropic model cards | "lint instructions", "audit prompts" |
| `reviewing-cc-config`  | Review CC config for context efficiency           | "review config", "config review"     |
| `using-gemini`         | Consult Gemini CLI for second opinions            | "ask gemini", "gemini search"        |
| `using-git-worktrees`  | Isolated git worktrees for parallel development   | "worktree", "isolate"                |

### Auto-Activated

These activate silently when relevant patterns are detected — no `/skill-name` needed.

| Skill                | Activates When                                      |
| -------------------- | --------------------------------------------------- |
| `managing-infra`     | K8s resources, Terraform, Helm, GitHub Actions      |
| `playwright-skill`   | Runtime library for testing-e2e skill               |
| `refactoring-code`   | Multi-file batch changes, rename everywhere         |
| `searching-code`     | "how does X work", trace flow, find all uses        |
| `smart-explore`      | AST code navigation via claude-mem (10-20x savings) |
| `using-cloud-cli`    | bq queries, gcloud/aws commands                     |
| `using-modern-cli`   | rg, fd, bat, eza, sd instead of legacy tools        |
| `writing-go`         | Go files, go commands, Go-specific terms            |
| `writing-python`     | Python files, pytest, pip, frameworks               |
| `writing-typescript` | TS/TSX files, npm/bun, React, Node.js               |
| `writing-web`        | HTML/CSS/JS/HTMX templates                          |

## Agents (Claude Code only)

| Need                       | Agent                       | Model  |
| -------------------------- | --------------------------- | ------ |
| Go implementation          | `go-engineer`               | sonnet |
| Python implementation      | `python-engineer`           | sonnet |
| TypeScript implementation  | `typescript-engineer`       | sonnet |
| Deep Go QA/impl review     | `go-qa`, `go-impl`          | opus   |
| Deep Python QA/impl review | `py-qa`, `py-impl`          | opus   |
| Deep TS QA/impl review     | `ts-qa`, `ts-impl`          | opus   |
| Go/Py/TS/Web review        | `*-idioms`, `*-tests`, etc. | sonnet |
| Go/Py/TS/Web docs review   | `*-docs`                    | haiku  |
| Infrastructure validation  | `infra-engineer`            | sonnet |
| E2E browser testing        | `playwright-tester`         | sonnet |
| Implementation planning    | `spec-planner`              | sonnet |
| Documentation updates      | `docs-keeper`               | sonnet |
| Web research               | `perplexity-researcher`     | sonnet |
| PDF data extraction        | `pdf-parser`                | sonnet |

## Hooks (Claude Code only)

| Hook                     | Event            | What It Does                                 |
| ------------------------ | ---------------- | -------------------------------------------- |
| `session-start.sh`       | SessionStart     | Shows git branch, last commit, file context  |
| `skill-enforcer.sh`      | UserPromptSubmit | Pattern-matches prompt and suggests skills   |
| `file-protector.sh`      | PreToolUse       | Blocks edits to settings.json, secrets       |
| `git-guardrails.sh`      | PreToolUse       | Blocks destructive git commands              |
| `smart-lint.sh`          | PostToolUse      | Auto-runs linter after file edits            |
| `test-runner.sh`         | PostToolUse      | Auto-runs tests after implementation changes |
| `notify.sh`              | Notification     | Desktop notifications for long operations    |
| `performance-monitor.sh` | PostCompact      | Tracks context compaction metrics            |
| `worktree-create.sh`     | WorktreeCreate   | Sets up isolated git worktree environment    |
| `worktree-remove.sh`     | WorktreeRemove   | Cleans up worktree on exit                   |

## Skill Export Architecture

All skills are authored for Claude Code and exported via a build system (`scripts/generate-overlays.py`) that produces platform-optimized `skills-codex/` directories. An `AGENTS.md` file is generated from these overlays for broad tool compatibility.

### Platform Support

| Component        | Claude Code                                   | Skill Export (Codex, Gemini, AGENTS.md)             |
| ---------------- | --------------------------------------------- | --------------------------------------------------- |
| **Skills** (33)  | Full — CC source with orchestration           | Optimized — stripped frontmatter + agentic preamble |
| **Agents** (34)  | Full — multi-agent review, parallel execution | Claude Code only                                    |
| **Hooks** (10)   | Full — lint, test, protect, suggest           | Claude Code only                                    |
| **Commands** (9) | Full — spec-driven development                | Claude Code only                                    |

### Skill Tiers

Skills are classified by how much adaptation they need:

| Tier       | Count | Strategy                                                      | Example                              |
| ---------- | ----- | ------------------------------------------------------------- | ------------------------------------ |
| **GREEN**  | 18    | Shared body, CC frontmatter stripped, platform preamble added | `writing-go`, `using-modern-cli`     |
| **YELLOW** | 9     | CC-ONLY body sections stripped, frontmatter cleaned           | `looking-up-docs`, `exploring-repos` |
| **RED**    | 6     | Hand-authored overlays optimized for o3/codex-1               | `reviewing-code`, `fixing-code`      |

### Structure

```
AGENTS.md                            # AGENTS.md standard (generated)
.claude-plugin/marketplace.json      # Claude Code marketplace
.agents/plugins/marketplace.json     # Codex CLI marketplace
gemini-extension.json                # Gemini CLI extension manifest
plugins/
├── dev-workflow/
│   ├── .claude-plugin/plugin.json   # Claude Code manifest
│   ├── .codex-plugin/plugin.json    # Codex CLI manifest
│   ├── gemini-extension.json        # Gemini CLI manifest
│   ├── skills/                      # CC source skills
│   ├── skills-codex/                # Platform-optimized (build output)
│   ├── agents/                      # Claude Code only
│   ├── hooks/                       # Claude Code only
│   └── commands/                    # Claude Code only
├── go-dev/
├── python-dev/
├── typescript-dev/
├── web-dev/
├── infra-ops/
├── dev-tools/
├── spec-system/
└── testing-e2e/
```

## Flat Directory

`flat/` provides a unified symlink view of all plugin components for tools that need flat directory access (chezmoi, Codex CLI, Gemini CLI). `AGENTS.md` is generated from `flat/skills-codex/`. Regenerate with:

```bash
scripts/generate-flat.sh
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to add plugins, run validation, and submit PRs.

## License

[MIT](LICENSE)
