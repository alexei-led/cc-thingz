# cc-thingz — Coding Companion

Portable skills, agents, and hooks for Pi, Claude Code, Codex CLI, and Gemini CLI — code review, language tooling, infrastructure, testing, and developer utilities. Platform-specific skills are excluded.

## Build

```bash
make build    # compile src/ → dist/ for all four targets (claude, codex, gemini, pi)
make fmt      # auto-fix ruff + shfmt + markdownlint
make check    # full lint (ruff, shellcheck, markdownlint, validate-config)
```

`make build` needs sandbox disabled — uv cache at `~/.cache/uv` is restricted in the CC sandbox.

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

Three role agents. A role is a capability envelope plus a reasoning stance no skill can supply. Domain procedure and output format live in skills; language specifics live in each skill's `references/<lang>.md`. Role × skill × references compose — language is not a routing key. Consolidated 39 → 3 (see `docs/agent-audit-2026-05-16.md` and the executed plan in `docs/plans/completed/`).

Envelope enforcement is per-target: Claude and Gemini grant a hard `tools:` allowlist (Gemini via the subagent frontmatter `tools:` field); Codex blocks writes via `sandbox_mode: read-only`; Pi has no tool-allowlist primitive, so the envelope there is a system-prompt directive. Gemini frontmatter has no read-only sandbox primitive, so `advisor` is granted `run_shell_command` and constrained to read-only by its body directive — the same tradeoff as Pi. Descriptions state each role behaviorally so the claim stays true on every target, and omit "use proactively" deliberately — roles are picked by the orchestrator to compose with a skill, not auto-delegated.

- **engineer** — read + write + execute. The only mutator: applies changes and runs the build/test/lint verification on what it changed. Fork target for `writing-{go,python,shell,typescript,web}` and `operating-infra`. Claude preloads `looking-up-docs`; `sequential-thinking` stays Skill-discoverable to keep spawn context lean.
- **reviewer** — Read + Grep + Glob + LS. Adversarial evaluator (assume bugs exist); emits structured findings/proposals, applies nothing. Non-mutating: tool-enforced on Claude and Gemini, write-blocked on Codex, directive on Pi. Absorbs the review family, code search, and planning (via `spec` / `planning:make`).
- **advisor** — strategic escalation: verdict, ranked risks, next actions. Ships to Codex, Gemini, and Pi; excluded from Claude, which has a built-in advisor. Codex enforces read-only via sandbox; Pi uses xhigh thinking with read-only Bash and transcript-forwarding invocation; Gemini grants a read-only `tools:` allowlist plus `run_shell_command` held read-only by the body directive.

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

- **writing-go** — Idiomatic Go development
- **writing-python** — Idiomatic Python 3.12+ development
- **writing-shell** — Portable shell scripting with POSIX sh, Bash, Zsh, Fish, ShellCheck, shfmt, Bats, and ShellSpec
- **writing-typescript** — Idiomatic TypeScript development
- **writing-web** — Simple web development with HTML, CSS, JS, and HTMX

## Infrastructure & Operations

- **deploying-infra** — Validate and deploy Kubernetes, Terraform, Helm, Kustomize, GitHub Actions, and Docker configs
- **operating-infra** — Author, inspect, troubleshoot, and review infrastructure across IaC, Kubernetes, cloud resources, containers, CI/CD, and Linux hosts

## Git Workflow

- **cleanup-git** — Remove merged local branches and stale git worktrees
- **configuring-git-hygiene** — Configure git hooks, Gitleaks, `.gitignore`, git config, and guardrails
- **using-git-worktrees** — Creates isolated git worktrees for parallel development

## Developer Tools

- **brainstorming-ideas** — Brainstorm ideas and stress-test draft plans or trade-offs before coding
- **evolving-config** — Audit and improve agent configuration across platforms; supports review-only audits and apply-fixes mode
- **exploring-repos** — Explore public GitHub repositories via DeepWiki AI-generated documentation
- **looking-up-docs** — Find current docs via Context7, official registries/docs, Perplexity/web, and GitHub fallback
- **researching-web** — Web research via Perplexity AI
- **reviewing-instructions** — Review and score AI-facing instruction files with scoped lint, model resolution, scoring caps, confidence, and calibration anchors
- **sequential-thinking** — Structured stepwise reasoning with explicit revisions and branches

## Browser Automation

- **browser-automation** — Rendered UI exploration, validation, screenshots, recordings, and browser-flow tests
- **playwright-skill** — Support-only Playwright runtime/reference for `browser-automation`
