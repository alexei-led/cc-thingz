# Documentation Update

Scope: documentation files only. Not for code-quality review (use reviewing-code).

Update project documentation to reflect current code state. Do not delete or overwrite existing docs without confirmation. If verification fails or required evidence is unavailable, report the failure instead of claiming docs are current.

## Roles

Detect your capability from your tools, not from prose:

- Write-capable role (engineer): run the 4-phase flow below — apply the doc edits and verify.
- Read-only role (reviewer): do not run the phases. You have no edit or Bash tools (no `git diff`). Work from the changed-file list the caller supplies, read the relevant code and existing docs, then emit the stale or missing docs as a proposal in the Reviewer Output contract at the end. Apply nothing; run nothing.

**Use TaskCreate / TaskUpdate** to track these 4 phases:

1. Determine documentation scope
2. Analyze recent changes
3. Analyze and update documentation
4. Verify and report

## Phase 1: Determine Scope

Ask one question at a time:

- **Doc scope** — What documentation should I update?
  1. **Auto-detect** — scan for outdated docs based on recent changes
  2. **README** — update project README
  3. **API docs** — update API/function documentation
  4. **All** — comprehensive documentation refresh

## Phase 2-3: Analyze and Update Documentation

Use a documentation subagent when available; otherwise inspect and update docs directly.

```
Task with engineer agent:
"Update documentation for this project.

## Your Task

1. Analyze current state:
   - Run `git diff --name-only HEAD~5` for recent changes
   - Find existing docs: `find . -name '*.md' -o -name 'doc.go'`
   - Check project structure and dependencies

2. Scope: {user's choice from Step 1}

3. Update focus:
   - Accurate function/method documentation
   - README sections matching current state
   - API endpoint documentation
   - Architecture notes if significant changes

4. Verify:
   - No broken links
   - Code examples compile/run
   - Markdown renders correctly

## Output Format

DOCUMENTATION UPDATE
====================
Updated:
- file.md (what changed)
- pkg/doc.go (added GoDoc)

Verified: All links valid, examples compile"
```

## Phase 4: Verify and Present Summary

Write-capable role only — a read-only reviewer skips Phase 4 and uses the Reviewer Output contract instead.

**Independent verification** (do not trust the agent's self-report):

When describing parent verification, explicitly mention checking runnable code examples or documented commands when practical. If examples/commands cannot be run, state why.

1. Run `git diff --stat` to confirm files were actually changed
2. For each changed file, verify the diff looks correct (no broken links, no placeholder text)
3. Run or compile documented code examples and commands when practical; if not practical, state why the check was skipped
4. If no files changed, report that no documentation modifications were needed

If no recent changes are found or documentation scope is unclear, ask the user what to document rather than generating speculative documentation.

Report using this format:

```
## Documentation Update

Updated:
- <file> — <one-line change summary>

Verified:
- git diff confirmed N files changed
- <check>: passed / skipped (<reason>)

Issues: <issue> or "none"
```

## Reviewer Output

Read-only role only. You applied nothing and ran nothing — emit the stale or missing docs as a proposal:

```text
## Proposed Changes

### Change 1: <brief description>

File: `path/to/doc`
Action: CREATE | MODIFY | DELETE

Code:
<the doc content, with enough surrounding context to locate it>

Rationale: <which code change makes this doc stale or missing>
```
