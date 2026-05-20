---
description: Explore public GitHub repositories in Pi using GitHub CLI, local clones,
  and web tools. Use when the user asks how a public repo works, wants architecture
  orientation, or needs repo-level Q&A. NOT for library API docs (use looking-up-docs)
  or local private codebases (use searching-code).
name: exploring-repos
---

<!-- Pi platform guidance -->
<!-- Use Pi tool names exactly: read, bash, edit, write, ask_user_question, structured_output, todo, Agent, get_subagent_result, steer_subagent, web_search, web_answer, web_research. -->
<!-- Use Agent, get_subagent_result, and steer_subagent for delegated work. -->
<!-- Use ctx7 or npx ctx7@latest through bash when Context7 documentation lookup is required. -->

# Explore Public Repositories in Pi

Use public sources and local clones. Do not assume specialized repo-wiki tools
exist.

## Workflow

1. Normalize the repo as `owner/name`.
2. Check if the repo is already cloned locally.
3. If not, ask before cloning large repos. For quick reads, prefer GitHub URLs
   or `gh repo view`.
4. Use `web_search` or `web_answer` for public docs, README context, release
   notes, or architecture articles.
5. Use `gh` or a shallow clone for code structure when needed.
6. For cloned-repo structural code search, follow `searching-code`: ast-grep / `sg` before `rg`, then `fd`, with `grep`/`find` only as fallback.
7. Map architecture from files, not reputation.
8. Use `looking-up-docs` for library API docs, not repo architecture.

## Commands

```bash
gh repo view owner/name --json name,description,homepageUrl,repositoryTopics
rg -n 'architecture|design|package|module|cmd|src' README.md docs 2>/dev/null
fd 'README|CONTRIBUTING|docs|cmd|src|packages|internal'
ast-grep run --pattern 'func $NAME($$$) { $$$ }' --lang go . 2>/dev/null
```

For a temporary clone:

```bash
git clone --depth=1 https://github.com/owner/name /tmp/name-repo
```

## Failure Handling

- Repo not found or private: report the `gh` error, ask the user to confirm the `owner/name` slug or check access.
- `gh` not installed: fall back to `git clone --depth=1` and `web_search` for public docs; note the limitation.
- Clone too large (>500 MB): warn before cloning, offer shallow clone or `gh repo view` summary only.

## Output Contract

```markdown
## Repository Map

### Repo

owner/name — <purpose>

### Entry Points

- `path` — role

### Architecture

- component and relationship facts with file references

### Public Docs

- source/result used

### Unknowns

- gaps or unverified claims
```
