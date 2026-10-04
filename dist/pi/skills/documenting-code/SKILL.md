---
{"description":"Write, rewrite, or update project docs from implementation facts - README front pages, user guides, configuration references, architecture docs, evaluations, agent instructions, and code comments. Use when docs are stale after a change, or when a doc set must become clear, visual, and consistent with the code. NOT for release preparation or release notes (use releasing-code), external library docs (looking-up-docs), scoring instruction files (reviewing-instructions), or ADRs unless explicitly requested.","name":"documenting-code"}
---
<!-- Pi platform guidance -->
<!-- Use installed tool names. Discover callable tools before batching independent calls in codemode; model-only UI/orchestration tools must be called directly. -->
<!-- Prefer direct read for required skill/instruction files when exposed; otherwise use Code Mode only after verifying output protection, not assumed nested-path protection. Code Mode composes calls, not durable workflows or context-mode data processing. Async subagents notify natively: yield rather than poll. -->


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
- A named doc or a named change is enough scope; start work. Ask only when the
  request names neither, with one question and these options: auto-detect from
  recent changes, README, API docs, or the full doc set.

## Readers

Decide the reader before writing.

- **Human**: short, scannable text. Use a diagram, table, or chart when it
  answers a question faster than prose. Load `references/doc-set.md` only for
  doc-set structure or Overhaul mode, `references/style.md` when rewriting prose,
  and `references/visuals.md` only when changing diagrams or charts.
- **Agent** (AGENTS.md, CLAUDE.md, skills, prompts): terse operational text with
  headers, bullets, numbered steps, exact contracts, and a table where it is the
  clearest form. No diagrams or rationale that a model already knows. To score
  or lint instruction files, use `reviewing-instructions`.
- **Code**: comments and docstrings state contracts, invariants, side effects,
  errors, and non-obvious decisions. Delete comments that restate the code.
  Load `references/code.md` for shared comment rules and per-language doc
  checks.

## Workflow

1. Scope the work from the request and the changed files (`git diff --name-only`),
   and find the existing docs that cover them.
2. List the doc files, the reader and the job of each, and the facts that more
   than one doc states. In Overhaul mode, write the ownership map from
   `references/doc-set.md` before editing.
3. Read the code, tests, and configuration that each doc describes. When docs and
   code conflict, report it and update the docs to the code, unless the user says
   that the doc is the intended contract.
4. Write. Keep each fact in one place and link to it from the others. Replace
   adjectives with measured facts.
5. Check changed claims against their source; use `references/claims.md` for
   configuration, API, or measured-performance claims. Generate sample output
   when changing examples. Mark unconfirmed claims and say where you looked.
6. If visuals changed, load `references/visuals.md`, render them, inspect the
   images, and fix the faults.
7. Run the gate once. Run it again only after further edits.
8. Report with the output contract.

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

Done when the relevant build/test/lint checks pass on what you changed, or you
name each check that did not run and why.

## Rules

- No speculative, future, or dead behavior.
- History (decision dates, "agreed with", replaced designs) belongs in git or
  the changelog, not in design docs.
- No secrets, tokens, private paths, or internal hosts.
- Generated docs: edit the source and run the generator.
- No ADRs or `docs/adr/` changes unless explicitly requested.
- Do not commit, push, or publish unless the user asks.

## Output

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

Without write access, return proposed changes (file, change, reason) instead of
applying them.

## Failure handling

- No stale docs found: say so and list what you checked.
- Large audit: one bounded read-only helper can map docs against code. Do not
  trust its report. Check its claims and the actual diff (`git diff --stat`)
  before you report success.
- A check fails: quote the failure in Issues.
