# dev-tools

Developer utilities: modern CLI tools, git worktrees, docs lookup, web research, brainstorming, and more. Skills available for both Claude Code and Codex CLI; agents and hooks are Claude Code-only.

## Skills (16)

| Skill                  | Invocable | What It Does                                     |
| ---------------------- | --------- | ------------------------------------------------ |
| `brainstorming-ideas`  | yes       | Brainstorm ideas and stress-test draft plans     |
| `grill-me`             | yes       | Relentless decision-tree interview on one plan   |
| `debating-ideas`       | yes       | Dialectic agents stress-test design decisions    |
| `looking-up-docs`      | yes       | Library documentation via Context7               |
| `researching-web`      | yes       | Web research via Perplexity AI                   |
| `analyzing-usage`      | yes       | Analyze Claude Code usage, cost, and efficiency  |
| `evolving-config`      | yes       | Audit config against latest Claude Code features |
| `using-gemini`         | yes       | Consult Gemini CLI for second opinions           |
| `learning-patterns`    | auto      | Extract learnings and generate customizations    |
| `linting-instructions` | yes       | Lint skill and agent instruction quality         |
| `reviewing-cc-config`  | yes       | Review CC config for context efficiency          |
| `exploring-repos`      | yes       | Explore GitHub repos via DeepWiki AI wiki        |
| `smart-explore`        | auto      | AST code navigation via claude-mem               |
| `mem-history`          | yes       | Query past sessions and decisions (claude-mem)   |
| `using-git-worktrees`  | auto      | Isolated git worktree management                 |
| `using-modern-cli`     | auto      | rg, fd, bat, eza, sd instead of legacy tools     |

## Agents (2)

- `perplexity-researcher` (sonnet) — codebase-aware web research
- `pdf-parser` (sonnet) — PDF parsing and structured data extraction

## Hooks (2)

| Hook                 | Event          | What It Does                  |
| -------------------- | -------------- | ----------------------------- |
| `worktree-create.sh` | WorktreeCreate | Sets up isolated git worktree |
| `worktree-remove.sh` | WorktreeRemove | Cleans up worktree on exit    |

## MCP Servers

| Server     | Used For                                              |
| ---------- | ----------------------------------------------------- |
| Context7   | looking-up-docs, evolving-config                      |
| Perplexity | researching-web, brainstorming-ideas, evolving-config |
