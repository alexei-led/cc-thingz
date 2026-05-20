---
description: Prefer modern CLI tools — ast-grep for structural code search, rg for
  text search, fd for file discovery, plus bat, eza, sd, dust, procs — over grep,
  find, cat, ls, sed, du, ps. Use when writing bash scripts, optimizing command chains,
  working with file searches, or replacing legacy Unix tools in workflows. NOT for
  application code logic, test writing, or infrastructure configuration.
name: using-modern-cli
---

# Modern CLI Tools

Use faster, ergonomic command-line tools installed on this system. Pick the tool
by target, not habit. Habit is how `grep -R` survives.

## Quick Reference

- Search code structure — `ast-grep` / `sg` (vs grep): AST-aware patterns,
  language constructs, safer refactor candidate search.
- Search text — `rg` (vs grep): fast literal/regex search, respects
  `.gitignore`.
- Find files — `fd` (vs find): simpler syntax, ignores `.git`.
- View files — `bat` (vs cat): syntax highlighting, line numbers.
- List files — `eza` (vs ls): icons, git status, tree view.
- Replace text — `sd` (vs sed): intuitive regex, preview mode.
- Disk usage — `dust` (vs du): visual tree, sorted by size.
- Processes — `procs` (vs ps): tree view, sortable columns.
- Diff files — `delta` (vs diff): syntax highlighting, side-by-side.

## Search Decision Tree

1. Code shape or language construct? Use `ast-grep` / `sg`.
2. Exact text, docs, logs, comments, config keys? Use `rg`.
3. File or directory names? Use `fd`.
4. Legacy `grep` / `find` only if the modern tool is missing.

## Examples

```bash
# Structural code search: ast-grep before rg
ast-grep run --pattern 'console.log($$$)' --lang javascript .
ast-grep run --pattern 'func $NAME($$$) { $$$ }' --lang go .
ast-grep scan --inline-rules 'id: await-in-func
language: javascript
rule:
  kind: function_declaration
  has:
    pattern: await $EXPR
    stopBy: end
' .

# Text search: rg instead of grep
rg "TODO" --type go           # Search Go files
rg -A 3 "error"               # 3 lines after match
rg -l "import"                # List files only

# Find files: fd instead of find
fd "\.go$"                    # Find Go files
fd -e json src/               # By extension in src/
fd -x wc -l {}                # Execute on matches

# View: bat instead of cat
bat main.go                   # With syntax highlighting
bat -n file.py                # Line numbers only

# List: eza instead of ls
eza -la --git                 # Long format with git status
eza --tree -L 2               # Tree view, 2 levels

# Replace: sd instead of sed
sd "old" "new" file.txt       # Simple replacement
sd -p "pattern" "new" file    # Preview changes first
sd -p 'colour' 'color' docs/**/*.md  # Preview only; do not apply without explicit ask

# Disk: dust instead of du
dust -d 2                     # 2 levels deep

# Processes: procs instead of ps
procs --tree                  # Process tree
```

## Rules

- For code-structure searches, try `ast-grep` before `rg`. Examples: function
  declarations, call expressions, code inside methods, missing error handling,
  framework usage patterns.
- For plain text, docs, logs, and config keys, use `rg`; ast-grep is the wrong
  hammer.
- For file discovery, use `fd` before `find`.
- For preview-only replacement tasks, use `sd -p` and state it is preview-only.
  Do not emit a non-preview `sd` command unless the user explicitly asked to
  apply.
- If a modern tool is not on `PATH`, fall back to the legacy equivalent and note
  the fallback.
- Do not install missing tools silently; report what is missing and suggest the
  relevant install command.

## Install Hints

```bash
brew install ast-grep ripgrep fd bat eza sd dust procs git-delta
npm install -g @ast-grep/cli
cargo install ast-grep
```

## Productivity Tools

```bash
# Fuzzy finder
vim $(fd . | fzf)
rg "pattern" | fzf

# Benchmarking
hyperfine "rg pattern" "grep -r pattern"

# Code statistics
tokei .

# Markdown preview
glow README.md

# JSON/YAML processing
jq '.key' file.json
yq '.key' file.yaml
```
