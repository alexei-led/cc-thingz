---
description: Prefer modern CLI tools for shell and file workflows — rg, fd, bat, eza,
  sd, dust, procs, and delta over legacy grep/find/cat/ls/sed/du/ps/diff. Use when
  writing bash scripts, optimizing command chains, or replacing legacy Unix tools.
  NOT for repo-wide code search, architecture review, AST/codegraph/GitNexus evidence,
  or application logic.
name: using-modern-cli
---

# Modern CLI Tools

Use faster, clearer command-line tools for shell workflows. This skill is about
operational ergonomics, not codebase analysis. Repo-wide code search, structural
AST evidence, code graphs, GitNexus, and architecture evidence are out of scope.

## Boundary

Use this skill for:

- replacing legacy shell commands with modern equivalents
- writing compact bash command chains
- previewing safe text replacements
- inspecting files, directories, disk usage, processes, and diffs

Do not use this skill for:

- repo-wide code understanding or flow tracing
- structural code-pattern searches
- architecture review or design evidence
- dependency graphs, callers/callees, blast radius, churn, or GitNexus queries

For those, use a dedicated codebase-analysis or architecture review workflow.

## Quick Reference

- Search text — `rg` instead of `grep`: fast literal/regex search, respects
  `.gitignore`.
- Find files — `fd` instead of `find`: simpler syntax, ignores `.git`.
- View files — `bat` instead of `cat`: syntax highlighting and line numbers.
- List files — `eza` instead of `ls`: git status and tree view.
- Replace text — `sd` instead of `sed`: clearer regex and preview mode.
- Disk usage — `dust` instead of `du`: sorted visual tree.
- Processes — `procs` instead of `ps`: tree view and sortable columns.
- Diffs — `delta` instead of raw `diff`: syntax-highlighted diffs.

## Examples

```bash
# Text search
rg "TODO" --type py
rg -C 3 "error" logs/
rg -l "OpenAI" docs/**/*.md

# File discovery
fd -e py
fd -e json src/
fd README .

# Viewing and listing
bat -n pyproject.toml
eza -la --git
eza --tree -L 2

# Preview-only replacement. Do not apply without explicit approval.
sd -p 'colour' 'color' docs/**/*.md

# Disk and processes
dust -d 2
procs --tree
```

## Rules

- Pick the tool by target: text, files, view, list, replace, disk, process, or diff.
- Use `rg` for plain text, docs, logs, comments, and config keys.
- Use `fd` for file or directory discovery.
- Use `sd -p` for replacement previews. Do not emit a non-preview `sd` command
  unless the user explicitly asked to apply the change.
- If a modern tool is missing, fall back to the legacy equivalent and state the
  fallback.
- Do not install missing tools silently.
- Do not explain AST, codegraph, GitNexus, or architecture search workflows here;
  keep this skill focused on shell/file commands.

## Install Hints

```bash
brew install ripgrep fd bat eza sd dust procs git-delta
```
