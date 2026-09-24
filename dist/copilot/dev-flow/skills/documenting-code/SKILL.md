---
{"description":"Write, rewrite, or update project docs from implementation facts - README front pages, user guides, configuration references, architecture docs, evaluations, agent instructions, and code comments. Use when docs are stale after a change, or when a doc set must become clear, visual, and consistent with the code. NOT for release preparation or release notes (use releasing-code), external library docs (looking-up-docs), scoring instruction files (reviewing-instructions), or ADRs unless explicitly requested.","name":"documenting-code"}
---

# Documenting Code

Turn implementation facts into docs that a named reader can use. Every claim in
the result matches the code, and every visual renders cleanly.

## Pick the mode

- **Update**: a code change made docs stale. Change the smallest set of docs.
  Done when each changed behavior is documented where its reader looks, and
  nothing unrelated changed.
- **Overhaul**: the user asks to rewrite, restructure, or improve a doc set, for
  example a README front page, guides, or an architecture doc. Done when:
  - each doc has one reader and one job, and each fact has one owner
  - every claim matches the code, and every visual passes its render check
  - the gate passes
- If the mode or the scope is unclear, ask one question with options:
  auto-detect from recent changes, README, API docs, or the full doc set.

## Readers

Decide the reader before writing.

- **Human**: short, scannable text. Use a diagram, table, or chart when it
  answers a question faster than prose. Load `references/doc-set.md` for doc
  roles and outlines, `references/style.md` for language, and
  `references/visuals.md` for diagrams and charts.
- **Agent** (AGENTS.md, CLAUDE.md, skills, prompts): terse operational text with
  headers, bullets, numbered steps, and exact contracts. No tables, diagrams,
  or rationale that a model already knows. To score or lint instruction files,
  use `reviewing-instructions`.
- **Code**: comments and docstrings state contracts, invariants, side effects,
  errors, and non-obvious decisions. Delete comments that restate the code.
  Load the reference for each changed language: `references/csharp.md`,
  `references/go.md`, `references/java-kotlin.md`, `references/python.md`,
  `references/rust.md`, `references/typescript.md`, `references/web.md`.

## Workflow

1. Scope the work from the request or the changed files (`git diff --name-only`).
2. List the doc files, the reader and the job of each, and the facts that more
   than one doc states. In Overhaul mode, write the ownership map from
   `references/doc-set.md` before editing.
3. Read the code, tests, and configuration that each doc describes. Code wins,
   unless the user says that the doc is the intended contract.
4. Write. Keep each fact in one place and link to it from the others. Keep
   history out of design docs. Replace adjectives with measured facts.
5. Check every claim against its source with `references/claims.md`. Generate
   sample output from the real code. Mark each claim that you cannot confirm,
   and say where you looked.
6. Render every new or changed diagram and chart, look at the images, and fix
   the faults named in `references/visuals.md`.
7. Run the gate once. Run it again only after further edits.
8. Report with the output contract.

For release preparation and release notes, use `releasing-code`.

## Gate

Run the bundled scripts on the changed docs from the project root.
`<skill-dir>` is the directory that contains this SKILL.md, as the host
reports it. Do not use a `scripts/` directory of the project instead.

```bash
python3 <skill-dir>/scripts/check-links.py <files or dirs>   # relative links and #anchors
bash <skill-dir>/scripts/render-mermaid.sh <files or dirs>   # renders each Mermaid block to PNG
python3 <skill-dir>/scripts/prose-lint.py <files or dirs>    # advisory plain-language lint
```

- Open the rendered images. A diagram that parses can still have a bad layout.
- Also run the repo's own docs checks, for example `markdownlint-cli2` or a
  `make` docs target, when they exist.
- Run documented commands and examples when practical.
- If a tool is missing (`mmdc`, `python3`), report which check did not run.

## Rules

- No speculative, future, or dead behavior.
- History (decision dates, "agreed with", replaced designs) belongs in git or
  the changelog, not in design docs. Use `releasing-code` for release notes.
- No secrets, tokens, private paths, or internal hosts.
- Generated docs: edit the source and run the generator.
- No ADRs or `docs/adr/` changes unless explicitly requested.
- Do not commit, push, or publish unless the user asks.

## Output

Write-capable role:

```markdown
## Documentation Update

Mode: update | overhaul

Updated:

- `path` — <what changed> (reader: <human | agent | code>)

Moved (overhaul only):

- <fact> → owned by `path`; other docs now link to it

Checked:

- claims: <n> checked against source; unconfirmed: none | <claim — where looked>
- visuals: <n> rendered and inspected | none changed
- gate: links <passed | failed>, diagrams <passed | skipped (reason)>, prose <n findings>

Issues: none | <remaining issue>
```

Read-only role: apply nothing and run nothing.

```markdown
## Proposed Changes

### Change 1: <brief description>

File: `path/to/doc`
Action: CREATE | MODIFY | DELETE
Reader: human | agent | code

Code:
<doc content or patch-sized replacement with enough context>

Rationale: <code fact that makes this stale, missing, or duplicated>
```

## Failure handling

- Unclear scope: ask the one question from "Pick the mode".
- No stale docs found: say so and list what you checked.
- Docs and code conflict: report the conflict. Update the docs to the code
  unless the user says that the docs are the contract.
- A claim cannot be checked: do not state it as fact. List it as unconfirmed.
- Large audit: one bounded read-only helper can map docs against code. Do not
  trust its report. Check its claims and the actual diff (`git diff --stat`)
  before you report success.
- A check fails: quote the failure and do not claim that the docs are current.
