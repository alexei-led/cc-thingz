---
name: reviewing-code
description: >-
  Multi-agent code review for security, quality, architecture, and deep-module design. Use when
  user says "review code", "check code", "code review", "review my changes",
  "review this PR", "improve architecture", "find refactoring opportunities",
  "deep modules", or wants feedback on source code/design. NOT for Claude
  Code configuration review (use reviewing-cc-config for skills/agents/hooks/
  CLAUDE.md review).
user-invocable: true
context: fork
allowed-tools:
  - Task
  - TaskOutput
  - TaskCreate
  - TaskUpdate
  - TaskList
  - AskUserQuestion
  - Read
  - Grep
  - Glob
  - LS
  - LSP
  - Bash(git *)
  - Bash(gh pr *)
  - Bash(gh api *)
  - Bash(rg *)
  - Bash(wc *)
  - mcp__plugin_claude-mem_mcp-search__search
  - mcp__plugin_claude-mem_mcp-search__get_observations
argument-hint: "[deep] [team] [external] [architecture]"
---

# Multi-Agent Code Review

**Use TaskCreate / TaskUpdate** to track these 4 phases:

1. Detect languages and scope
2. Spawn review agents (or team)
3. Collect agent results
4. Aggregate and present findings

---

**Parse `$ARGUMENTS`:**

- `deep` → 6-12 specialized Claude sub-agents (language-specific reviewers)
- `team` → **Agent team mode**: Reviewers challenge each other's findings
- `external` → Add external AI reviewers (Codex + Gemini). **Only if explicitly requested.**
- `architecture` → Focus on module depth, seams, adapters, testability, and locality.

**IMPORTANT:** Without `external` flag, run ONLY Claude agents. Never run Codex or Gemini unless `external` is in arguments.

| Arguments          | Claude Agents                                                       | Mode     | External (Codex + Gemini) |
| ------------------ | ------------------------------------------------------------------- | -------- | ------------------------- |
| (none)             | go-engineer, python-engineer                                        | Subagent | ❌ No                     |
| deep               | go-qa, go-idioms, go-tests, go-impl, go-docs, go-simplify (+ py-\*) | Subagent | ❌ No                     |
| team               | go-engineer, python-engineer                                        | **Team** | ❌ No                     |
| deep team          | All 6-12 specialized sub-agents                                     | **Team** | ❌ No                     |
| external           | go-engineer, python-engineer                                        | Subagent | ✅ Yes                    |
| team external      | go-engineer, python-engineer                                        | **Team** | ✅ Yes                    |
| deep team external | All 6-12 specialized sub-agents                                     | **Team** | ✅ Yes                    |

---

## Step 0: Check Historical Context (if claude-mem available)

If `mcp__plugin_claude-mem_mcp-search__search` is available, query for past findings on changed files:

```
search({ query: "<file paths from git diff --name-only HEAD>", limit: 10 })
```

Look for past review findings, gotchas (`type: "gotcha"`), and decisions on those files. If relevant observations exist, fetch details with `get_observations` and include key findings in agent prompts (Step 2).

Skip this step silently if claude-mem tools are not available.

---

## Architecture Review Vocabulary

Use these terms exactly when `architecture` is set or the request asks for design/refactoring opportunities:

- **Module** — anything with an interface and implementation: function, class, package, or slice.
- **Interface** — everything callers must know: types, invariants, ordering, error modes, config, performance.
- **Seam** — where an interface lives; a place behavior can change without editing in place.
- **Adapter** — a concrete thing satisfying an interface at a seam.
- **Depth** — leverage at the interface: lots of behavior behind a small interface.
- **Leverage** — caller value from depth.
- **Locality** — change, bugs, and verification concentrated in one place.

Apply the deletion test: if deleting a module makes complexity vanish, it was a pass-through. If complexity reappears across callers, the module was earning its keep.

Seam rule: one adapter means a hypothetical seam; two adapters means a real seam. Do not propose ports without real variation.

When `CONTEXT.md`, `CONTEXT-MAP.md`, or `docs/adr/` exist, read the relevant docs before naming architecture findings. If a candidate contradicts an ADR, flag it only when the friction is real enough to justify reopening the decision.

## Step 1: Detect Language & Ask Scope

Detect languages in changes:

```bash
git diff --name-only HEAD | grep -E '\.(go|py|ts|tsx|html|css|js)$' | head -20
```

Then use AskUserQuestion:

| Header       | Question                   | Options                                                                                                                                |
| ------------ | -------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| Review scope | What code should I review? | 1. **Uncommitted changes** - git diff HEAD 2. **Branch vs master** - git diff master...HEAD 3. **Specific files** - I'll provide paths |

Build git command based on choice.

---

## Step 2: Spawn Agents or Team (ALL in ONE message)

### Team Mode vs Subagent Mode

**If `team` in `$ARGUMENTS`**: Use agent team for collaborative review with debate.

**Team mode benefits:**

- Reviewers challenge each other's findings
- Competing perspectives surface edge cases
- Faster for complex PRs (parallel independent work)

**Subagent mode benefits:**

- Simpler coordination
- Lower token cost
- Better for straightforward reviews

---

### Default Mode: Language Engineers

For each detected language, spawn ONE Task:

- Go files → `Task(subagent_type="go-engineer", ...)`
- Python files → `Task(subagent_type="python-engineer", ...)`

### Deep Mode: Specialized Sub-Agents

Invoke agents by their `subagent_type` (models defined in agent metadata):

If `architecture` is set, add this instruction to every reviewer prompt:

```text
Architecture focus:
- Find shallow modules, pass-through abstractions, poor seams, fake ports, hidden coupling, and untestable interfaces.
- Use module/interface/seam/adapter/depth/leverage/locality vocabulary.
- Apply the deletion test.
- Propose deepening opportunities, not cosmetic refactors.
- Explain how tests improve after the change.
```

**Go agents** (if Go files detected):

| subagent_type | Focus                        |
| ------------- | ---------------------------- |
| go-qa         | Logic, security, performance |
| go-tests      | Test coverage, quality       |
| go-impl       | Implementation concerns      |
| go-idioms     | Patterns, error handling     |
| go-docs       | Documentation, comments      |
| go-simplify   | Over-abstraction, dead code  |

**Python agents** (if Python files detected):

| subagent_type | Focus                        |
| ------------- | ---------------------------- |
| py-qa         | Logic, security, performance |
| py-tests      | Test coverage, quality       |
| py-impl       | Implementation concerns      |
| py-idioms     | Patterns, typing             |
| py-docs       | Docstrings, documentation    |
| py-simplify   | Over-abstraction, dead code  |

**TypeScript agents** (if TypeScript files detected):

| subagent_type | Focus                        |
| ------------- | ---------------------------- |
| ts-qa         | Logic, security, performance |
| ts-tests      | Test coverage, quality       |
| ts-impl       | Implementation concerns      |
| ts-idioms     | Patterns, strict typing      |
| ts-docs       | Documentation, comments      |
| ts-simplify   | Over-abstraction, dead code  |

**Web agents** (if HTML/CSS/JS files detected):

| subagent_type | Focus                           |
| ------------- | ------------------------------- |
| web-qa        | Security, performance, a11y     |
| web-tests     | E2E/Playwright test quality     |
| web-impl      | Requirements, responsiveness    |
| web-idioms    | Semantic HTML, CSS, JS patterns |
| web-docs      | Comments, ARIA labels           |
| web-simplify  | CSS bloat, unnecessary JS       |

**If `team` NOT in `$ARGUMENTS`** (Subagent mode):

Spawn each agent using its subagent_type directly:

```
Task(subagent_type="{agent}", prompt="Review code from: {git_command}. Output: file:line - Issue. Fix.")
```

Agent's own `model` setting (from metadata) is respected automatically.

**If `team` in `$ARGUMENTS`** (Team mode):

Create an agent team with specialized reviewers:

```
Create an agent team to review code from: {git_command}.

Spawn teammates for detected languages:

{If Go detected}:
- go-qa: Security, logic, OWASP Top 10
- go-idioms: Patterns, error handling, stdlib usage
- go-tests: Test coverage, quality, edge cases
- go-impl: Requirements match, DI, edge cases
- go-docs: Documentation quality
- go-simplify: Over-abstraction, dead code

{If Python detected}:
- py-qa: Security, logic, OWASP Top 10
- py-idioms: Pythonic patterns, type hints
- py-tests: pytest patterns, coverage
- py-impl: Requirements, DI wiring
- py-docs: Docstrings, type hints
- py-simplify: Over-abstraction, complexity

{If TypeScript detected}:
- ts-qa: Security, async safety, OWASP
- ts-idioms: Strict typing, patterns
- ts-tests: Test quality, coverage
- ts-impl: Requirements match
- ts-docs: Documentation
- ts-simplify: Over-engineering

{If Web detected}:
- web-qa: Security, performance, a11y
- web-idioms: Semantic HTML, CSS, JS patterns
- web-tests: E2E/Playwright quality
- web-impl: Requirements, responsiveness
- web-docs: Comments, ARIA labels
- web-simplify: CSS bloat, unnecessary JS

Have reviewers:
1. Review code independently
2. Challenge each other's findings
3. Flag disagreements for discussion
4. Converge on consensus issues

Report format: file:line - Issue. Fix. [Flagged by: agent1, agent2]
```

The team lead will coordinate reviewers and synthesize results.

### External Mode: Add Codex + Gemini (ONLY if `external` in arguments)

**Skip this section entirely if `external` is NOT in `$ARGUMENTS`.**

If `external` IS present, spawn these agents IN PARALLEL with Claude agents:

```
Task(subagent_type="codex-assistant", prompt="review: Review code from {git_command}")
Task(subagent_type="gemini-consultant", prompt="review: Review architecture of {git_command}")
```

**codex-assistant**: Code review for security (OWASP), quality, architecture, testing gaps.
**gemini-consultant**: Architecture alternatives and design trade-offs.

**Remember:** `deep` alone = Claude agents only. `deep external` = Claude + Codex + Gemini.

---

## Step 3: Aggregate & Present

```markdown
## Code Review Summary

**Mode**: {default|deep} {team} {+external}
**Scope**: {description}
**Agents**: {count} reviewers
**Coordination**: {Subagents | Agent Team}

---

### CRITICAL (Must Fix)

- [{source}] `file:line` - Issue. Fix.

### IMPORTANT (Should Fix)

- [{source}] `file:line` - Issue. Fix.

### SUGGESTIONS

- [{source}] `file:line` - Issue. Fix.

---

### Consensus (Multi-Agent Agreement)

| Issue | Flagged By | Confidence |
| ----- | ---------- | ---------- |
| ...   | ...        | High       |

### Architecture Opportunities (if requested)

| Candidate | Files | Problem | Deepening Move | Test Benefit |
|-----------|-------|---------|----------------|--------------|
| ...       | ...   | ...     | ...            | ...          |

### Recommended Actions

1. {prioritized list}
```

### Writing Style

- **Brevity**: One sentence per finding. No preamble, no "I noticed that..."
- **No AI-speak**: Cut "potential", "might", "consider". State what IS wrong
- **Direct**: "This leaks memory" not "This could potentially lead to memory issues"
- **Technical precision**: Include type names, function signatures, line numbers

---

## Examples

```
/reviewing-code                      # Subagents: go-engineer, python-engineer
/reviewing-code deep                 # Subagents: 6-12 specialized (NO external)
/reviewing-code team                 # Agent team: engineers challenge each other
/reviewing-code deep team            # Agent team: all 6-12 specialists with debate
/reviewing-code external             # Subagents: Claude + Codex + Gemini
/reviewing-code deep team external   # Agent team: all specialists + external reviewers
```

**Execute this workflow now.**
