---
description:
  Batch refactoring for multi-file, repeated-pattern, large-file, or broad
  behavior-preserving changes. Use for "refactor across files", "batch rename",
  "update pattern everywhere", large files (500+ lines), or 5+ edits in the same
  file. NOT for repo-wide architecture design/review, codebase analysis,
  single-file targeted edits, or code review (use reviewing-code).
name: refactoring-code
---

# Batch Refactoring

Refactor in small, verified batches. If behavior changes, it is not a refactor;
it is a feature or bug fix. State the behavior-preservation target before editing.

## Role-gated action

Detect your capability from your tools, not from prose:

- Write-capable role (engineer): map the scope, apply the batch edits, run lint/test verification.
- Read-only role (reviewer): map the scope and produce the refactor plan, then emit it in the Proposed Changes contract under Output. Apply nothing; run nothing.

## When To Use

Use this workflow for:

- multi-file refactors
- repeated pattern updates
- public or internal renames with callers
- large files where exact text replacement is brittle
- 5+ coordinated edits in the same file

Do not use it for:

- one small targeted edit
- behavior changes
- broad architecture redesign
- code review findings without applying changes
- cosmetic churn with no maintenance value

## Workflow

1. Define the refactor goal and non-goals.
2. Name the behavior that must be preserved.
3. Map all affected sites before editing with file/text search.
4. Read representative files and tests.
5. Add characterization tests when behavior is under-specified.
6. Apply one coherent batch using the best available edit tool; use a semantic batch editor only when the runtime provides one.
7. Run narrow tests.
8. Run broader lint/type/test checks before the next batch.
9. Delete dead code introduced or exposed by the refactor.

## Safe Batches

Good batches:

- rename one public symbol and all callers
- move one function/module with tests unchanged
- remove one duplicate implementation after tests prove equivalence
- update one repeated pattern across files

Bad batches:

- rename many symbols while changing logic
- reorganize modules and change APIs in one pass
- add abstractions for imagined future callers
- edit generated files by hand

## Output

Engineer (applied the refactor):

```text
REFACTOR COMPLETE
=================
Preservation target: <behavior that must not change>
Files changed: N
Status: CLEAN | NEEDS ATTENTION

Changes:
- path:line — change

Verification:
- <command> — pass/fail
```

Reviewer (planned only — emit the refactor as a proposal, apply nothing):

```text
## Proposed Changes

Preservation target: <behavior that must not change>

### Change 1: <brief description>

File: `path/to/file`
Action: CREATE | MODIFY | DELETE

Code:
<changed regions with enough context to locate them>

Rationale: <why this preserves behavior while improving structure>
```

For multi-file renames, list every occurrence mapped before the proposal so the
applier can replay it.

## Failure handling

- Batch-edit tool unavailable: use the runtime's precise edit tools and shrink the batch.
- Tests fail after a batch: revert or inspect the last batch before continuing.
- Scope unclear (`refactor this`): ask which files and what behavior to preserve before touching anything.
- A mapped occurrence is generated or vendored: skip it unless the project regenerates that file from source.
