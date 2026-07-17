# cc-thingz — Coding Companion

Portable skills, agents, and typed hooks for Pi, Claude Code, Codex CLI, Copilot, Cursor, and Grok — code review, language tooling, infrastructure, testing, and developer utilities. Gemini is retired.

## Build

```bash
make build    # render package targets and typed hooks with Agent Bundler
make fmt      # auto-fix ruff + shfmt + markdownlint
make check    # fail on generated drift without rewriting dist
make ci       # lint + validate + check + test + test-ts
```

`make build` requires an installed `agbun` with `package`, flat per-agent sidecars, declared hook environments, bundled Pi dependencies, native Pi resources, and Codex project-agent profiles. Builds need sandbox disabled because the uv cache at `~/.cache/uv` is restricted in the CC sandbox.

## Writing Agent/Skill Instructions

LLM signal hierarchy (MDEval benchmark + Perplexity research):

- HIGH: `#` headers, bullet/numbered lists, code blocks — always use
- MEDIUM: `**bold**` — ≤15% of prose lines; use for bullet labels (`- **Label**: desc`) and critical keywords only
- LOW/zero: `_italic_`, `---` horizontal rules, markdown tables, mermaid/ASCII diagrams — never use

Specific rules:

- `**Label:**` on its own line → `### Label` (real header, not bold pseudo-header)
- `**Sentence.** followed by prose` → strip bold, keep as plain sentence
- `---` before `##` or `**bold` → remove (redundant section break)
- `---` before ` ```` ` fence → keep (it's template content showing proposal format)

Run format lint: `make lint-instructions` or use the `/reviewing-instructions` skill for full scoring.

## Agents

Three role agents plus one utility agent. A role is a capability envelope plus a reasoning stance no skill can supply. Domain procedure and output format live in skills; language specifics live in each skill's `references/<lang>.md`. Role × skill × references compose — language is not a routing key. Consolidated 39 → 3 roles (see `docs/agent-audit-2026-05-16.md` and the executed plan in `docs/plans/completed/`). `runner` is the cheap utility lane for simple bounded tasks, not a fourth role.

Envelope enforcement is per-target: Claude grants a hard `tools:` allowlist; Codex blocks writes via `sandbox_mode: read-only`; Pi has no tool-allowlist primitive, so the envelope there is a system-prompt directive. Copilot and Cursor are portable artifact targets without a cc-thingz-owned runtime envelope yet. The role descriptions omit "use proactively" deliberately — roles are picked by the orchestrator to compose with a skill, not auto-delegated. `runner` is the exception: it is a utility lane and can opt into proactive routing.

- **engineer** — read + write + execute. The only mutator: applies changes and runs the build/test/lint verification on what it changed. Fork target for `writing-{csharp,go,java-kotlin,python,rust,shell,typescript,web}` and `operating-infra`. Claude preloads `looking-up-docs`; `sequential-thinking` stays Skill-discoverable to keep spawn context lean.
- **reviewer** — Read + Grep + Glob + LS. Adversarial evaluator (assume bugs exist); emits structured findings/proposals, applies nothing. Non-mutating: tool-enforced on Claude, write-blocked on Codex, directive on Pi. Absorbs the review family, code search, and planning (via `spec-flow`).
- **runner** — fast utility lane: file lookup, grep/glob, `git status/log/show/diff`, file reads, log summaries, and focused shell inspection. Read-only across targets. Use proactively for simple bounded tasks; escalate to `engineer`, `reviewer`, or `advisor` when the task stops being cheap or obvious.
- **advisor** — strategic escalation: verdict, ranked risks, next actions. Ships to Codex and Pi; excluded from Claude, which has a built-in advisor. Codex enforces read-only via sandbox; Pi uses xhigh thinking with read-only Bash and transcript-forwarding invocation.

### Platform Coverage

Agent × target coverage. Every gap is intentional and documented below.

- **engineer**: claude (full Edit/Write/Bash) and pi (full Bash/Edit/Write). Excluded from codex — Codex enforces `sandbox_mode: read-only`; a mutator role is inoperable under that constraint.
- **reviewer** and **runner**: Claude, Codex, Pi, Copilot, Cursor, and Grok portable outputs. Read-only enforcement is native on Claude and Codex, directive-based on Pi; new-target runtime policy remains vendor-owned.
- **advisor**: Codex and Pi. Excluded from Claude — Claude Code has a built-in advisor; adding a custom one would duplicate or conflict with the native capability.

Skills and typed hooks render to all six enabled Agent Bundler targets by default. A `targets:` key restricts source eligibility. `.agentbundler/targets/*.json` contains explicit sidecars and `agentbundle.json` contains target-wide composition. `sequential-thinking` is the canonical no-overlay example.

For the compiled output paths and overlay mechanics, see [Compiler Pipeline](CONTRIBUTING.md#compiler-pipeline).

### Routing and model tiers

Routing lives in the orchestrator instructions (`CLAUDE.md`, `AGENTS.md`, parent prompt), not in the role file alone.

- For automatic cheap-task routing, add a dedicated utility/read-only agent such as `runner` and tell the orchestrator to use it proactively for simple bounded tasks: file listing, grep/glob, `git status/log/show/diff`, file reads, log summaries, and focused shell inspection.
- Keep `engineer` as the sole normal mutator. Do not create weaker duplicates such as `junior-engineer` just to swap model tiers.
- If a small explicit write task should use a cheaper model, override the model for that one call instead of adding a second general-purpose engineer role.
- For Pi package agents, keep repo frontmatter model-agnostic. Do not pin `model` or `thinking` in cc-thingz; put user/project model policy in `~/.pi/agent/settings.json` or `.pi/settings.json` with `subagents.agentOverrides` or router profiles.
- Agent Bundler is required for builds. It renders package assets, typed hooks, target manifests, deterministic archives, the Pi aggregate hook runtime, declared Pi-native extension trees, and Codex project-agent profiles. Pi's native compatibility runner is part of the extension tree; only documented lifecycle and target-contract gaps remain. See `docs/agentbundler-gaps.md` and `src/hooks/UNSUPPORTED.md`.
- Do not auto-route architecture, ambiguous debugging, broad refactors, deep review, security-sensitive reasoning, or product decisions to a light model.
- Put cross-tool shared routing policy in the chezmoi-managed top-level `CLAUDE.md`. Keep repo-local role boundaries and package rules here in `AGENTS.md`.
- On Claude Code, a dedicated utility agent can opt into automatic delegation via its `description` with `Use proactively ...`. The role agents intentionally omit that phrase because they are orchestrator-selected, not auto-delegated.

## Development Workflow

- **committing-code** — Smart git commits with logical grouping
- **documenting-code** — Update project documentation based on recent changes
- **fixing-code** — Reproduce, diagnose, patch, regression-test, and verify code defects
- **improving-tests** — Improve test design and coverage with behavior seams, characterization tests, TDD, and refactoring
- **refactoring-code** — Behavior-preserving batch refactors with mapped sites and optional graph-backed impact checks
- **reviewing-code** — Evidence-backed code review with severity/confidence rubric, depth modes, and optional team/external review
- **spec-init** — Bootstrap a new `.spec/` project or import requirements from a design doc
- **spec-interview** — Capture PRD-quality requirements via structured Q&A
- **spec-plan** — Turn a requirement into an EPIC with vertical-slice TASKs
- **spec-new** — Create a single TASK or REQ file from a template
- **spec-work** — Implement the next ready task with approval at each step
- **spec-status** — Report spec progress; quality audit for orphans and cycles
- **spec-done** — Mark a task complete with evidence and quality gates

## Language Tooling

- **writing-csharp** — Idiomatic C# /.NET development
- **writing-go** — Idiomatic Go development
- **writing-java-kotlin** — Modern Java and Kotlin JVM development
- **writing-python** — Idiomatic Python 3.12+ development
- **writing-rust** — Idiomatic Rust development
- **writing-shell** — Portable shell scripting with POSIX sh, Bash, Zsh, Fish, CI `run:` bodies, ShellCheck, shfmt, Bats, and ShellSpec
- **writing-typescript** — Idiomatic TypeScript development
- **writing-web** — Simple web development with HTML, CSS, JS, and HTMX

## Infrastructure & Operations

- **deploying-infra** — Validate infrastructure changes and, after explicit confirmation, apply Terraform, Helm, Kustomize, or Kubernetes deployments; Dockerfiles and GitHub Actions are validate-only
- **operating-infra** — Author, inspect, troubleshoot, and review infrastructure across IaC, Kubernetes, cloud resources, containers, GitHub Actions workflow semantics, and Linux hosts

## Git Workflow

- **cleanup-git** — Remove merged local branches and stale git worktrees
- **configuring-git-hygiene** — Configure git hooks, Gitleaks, `.gitignore`, git config, and guardrails
- **using-git-worktrees** — Creates isolated git worktrees for parallel development

## Developer Tools

- **brainstorming-ideas** — Brainstorm ideas and stress-test draft plans or trade-offs before coding
- **evolving-config** — Audit AI coding-agent configuration and plugin/package manifests; review-only by default, explicit approval for fixes
- **looking-up-docs** — Find exact API/config syntax and versioned docs via Context7, official registries/docs, and GitHub fallback
- **researching-web** — Web research for comparisons, current-state, and release-behavior questions with grounded source selection and stale-source reporting
- **reviewing-instructions** — Review and score AI-facing markdown/prompt instruction files with scoped lint, model resolution, scoring caps, confidence, and evidence
- **writing-skills** — Create, split, slim, and route repository skills, references, overlays, and plugin placement
- **sequential-thinking** — Structured stepwise reasoning with explicit revisions and branches

## Browser Automation

- **browser-automation** — Rendered UI exploration, validation, screenshots, recordings, and browser-flow tests
- **playwright-skill** — Support-only Playwright runtime/reference for `browser-automation`
