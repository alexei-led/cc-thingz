---
description:
  Update project documentation based on code changes. Use when the user
  asks to update docs, document behavior, add README content, or align docs with recent
  implementation changes. NOT for code-quality feedback (use reviewing-code).
name: documenting-code
---

# Documenting Code

Update docs from code facts, not vibes. Keep docs close to the behavior they
explain.

## Role-gated action

Detect your capability from your tools, not from prose:

- Write-capable role (engineer): apply the doc edits and run the validation check.
- Read-only role (reviewer): identify the stale or missing docs and emit the edits in the Proposed Changes contract under Output. Apply nothing; run nothing — a reviewer has no edit or Bash tools (no `git diff`; work from the changed-file list the caller supplies).

## Language detection and references

Detect the language of the changed implementation from file extensions and load the matching reference for language-specific doc conventions:

- Go → [references/go.md](references/go.md)
- Python → [references/python.md](references/python.md)
- TypeScript → [references/typescript.md](references/typescript.md)
- Web → [references/web.md](references/web.md)

Mixed languages: load each matching reference. Unknown language: use the generic rules below only.

## Workflow

1. Identify changed files with `git diff --name-only` unless the user supplied
   paths.
2. Read the relevant implementation, tests, and existing docs.
3. Use `looking-up-docs` only when external API behavior or syntax is uncertain.
4. For large doc audits, launch one bounded `Agent` (read-only Explore) to map
   changed behavior. Verify its claims before editing.
5. Update the smallest set of docs that users or maintainers need.
6. Run docs or repo validation.

## What To Update

- README usage or setup when user-visible behavior changes.
- API docs when parameters, output, or errors change.
- Architecture docs when module boundaries or data flow change.
- Generated catalogs only through their generator scripts.
- Plugin docs when skill, agent, hook, or command behavior changes.

## Rules

- Do not document dead or speculative behavior.
- Do not author or update ADRs (architecture decision records) or `docs/adr/`
  unless the user explicitly asks for them.
- Do not add promotional filler.
- Prefer examples that can be run.
- Keep private paths or secrets out of docs.
- If docs disagree with code, code wins unless the user says the docs are the
  intended contract.

## Verification

Run the narrowest relevant checks, for example:

```bash
markdownlint-cli2 '**/*.md'
make validate
```

If a tool is missing, state that and run the next available check.

## Output

Engineer (applied the doc edits): report the docs changed and the validation result.

Reviewer (identified only — emit the edits as a proposal, apply nothing):

```text
## Proposed Changes

### Change 1: <brief description>

File: `path/to/doc`
Action: CREATE | MODIFY | DELETE

Code:
<the doc content, with enough surrounding context to locate it>

Rationale: <which code change makes this doc stale or missing>
```
