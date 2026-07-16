---
description: Batch behavior-preserving refactors for multi-file, repeated-pattern,
  large-file, rename, move, extract, split, or restructure work. Use for "refactor
  across files", "batch rename", "update pattern everywhere", large files (500+ lines),
  or 5+ coordinated edits in one file. NOT for single targeted edits, behavior changes
  or bug fixes (use fixing-code), test-only refactors (use improving-tests), code
  review (use reviewing-code), or architecture redesign (use architecture-design/review).
name: refactoring-code
---

# Batch Refactoring

Use this when many edits must preserve externally observable behavior. Stop if you
cannot name the maintenance value and the behavior that must stay unchanged.

## Role-gated action

Detect capability from tools:

- Write-capable role: map scope, apply one batch, run verification.
- Read-only role: map scope and emit the refactor in the Proposed Changes contract. Apply nothing; run nothing.

## Route elsewhere

Do not use this for:

- one small edit that normal coding tools can handle
- behavior changes, bug fixes, or failing checks → `fixing-code`
- test-only cleanup, coverage, or TDD → `improving-tests`
- review findings without edits → `reviewing-code`
- target architecture design or repo-wide structural audit → architecture skills
- cosmetic churn with no maintenance value

## Language references

Load the matching reference for the language being refactored:

- C# /.NET: `references/csharp.md`
- Go: `references/go.md`
- Java/Kotlin: `references/java-kotlin.md`
- Python: `references/python.md`
- Rust: `references/rust.md`
- TypeScript/JavaScript: `references/typescript.md`

Unsupported language: use the general workflow in this file only.

## Evidence first

Before editing:

1. Define goal, non-goals, preservation target, and safety gate.
2. Map every affected site with text search and language-aware tools.
3. For renames, moves, extracts, splits, or broad restructures, use graph tools when available:
   - GitNexus dry-run rename for renames; GitNexus context, impact, and query for callers, callees, execution flows, and string/dynamic refs.
   - codegraph status first; if fresh, use codegraph context or affected to size dependency/call blast radius.
4. Treat stale graph indexes as no evidence. Refresh if allowed; otherwise fall back to search/LSP and report the gap.
5. Check non-code references when names or paths change: config, routes, DI wiring, serialization keys, CLI entries, generated sources, scripts, and docs.
6. Read representative implementation files and tests.
7. Add characterization tests at the public boundary when behavior is under-specified and risk is not low.

No mapped site, no edit.

## Batch rules

Good batches are small, reversible, and single-purpose:

- rename one symbol/concept and all callers
- move one module/function and its tests
- extract one cohesive responsibility behind the same public behavior
- remove one duplicate implementation after tests prove equivalence
- update one repeated pattern across mapped sites

Rules:

- Separate mechanical structure changes from logic changes.
- Do not rename many concepts while changing APIs or control flow.
- Prefer semantic refactoring tools; use precise text edits only for mapped sites.
- For public APIs, keep compatibility shims or deprecations unless the user approved a breaking change.
- Run narrow tests after each batch; run broader lint/type/test checks before the next batch or final report.
- Delete dead code exposed by the refactor. Do not hand-edit generated or vendored files unless the project regenerates them from source.

## Output

Engineer:

```text
REFACTOR COMPLETE
=================
Preservation target: <behavior that must not change>
Safety gate: <tests/checks used>
Files changed: N
Status: CLEAN | NEEDS ATTENTION

Mapping:
- <tool/search> — <key affected sites or graph gap>

Changes:
- path:line — change

Verification:
- <command> — pass/fail
```

Reviewer:

```text
## Proposed Changes

Preservation target: <behavior that must not change>
Safety gate: <tests/checks the applier should run>

Mapping:
- <tool/search> — <affected sites or graph gap>

### Change 1: <brief description>

File: `path/to/file`
Action: CREATE | MODIFY | DELETE

Code:
<changed regions with enough context to locate them>

Rationale: <why this preserves behavior while improving structure>
```

For multi-file renames, list every mapped occurrence or explicitly mark ambiguous/unmapped references.

## Failure handling

- Scope unclear: ask which files/concept and what behavior to preserve.
- Tests/checks missing for risky code: ask to add characterization tests or shrink/defer the refactor.
- Tests fail after a batch: inspect or revert that batch before continuing.
- Required behavior change appears: stop and split into refactor first, then feature/fix.
- Graph tool missing or stale: report the gap and use search/LSP evidence instead.
- Generated or vendored occurrence: skip it unless regeneration is part of the verified workflow.