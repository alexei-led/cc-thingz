---
description: Batch refactoring via MorphLLM edit_file. Use for "refactor across files",
  "batch rename", "update pattern everywhere", large files (500+ lines), or 5+ edits
  in the same file. NOT for repo-wide architecture design/review, codebase analysis,
  single-file targeted edits (use built-in Edit), or code review (use reviewing-code).
name: refactoring-code
---

# Fast Refactoring with MorphLLM

MorphLLM `edit_file` provides semantic code merging at 10,500+ tokens/sec with
98% accuracy. Use the MorphLLM `edit_file` / batch refactoring workflow for broad
behavior-preserving changes, not cosmetic churn.

Critical rule: preserve existing behavior unless the user explicitly asks for a
behavior change. State the preservation target before editing.

## Role-gated action

Detect your capability from your tools, not from prose:

- Write-capable role (engineer): map the scope, apply the batch edits, run lint/test verification.
- Read-only role (reviewer): map the scope and produce the refactor plan, then emit it in the Proposed Changes contract under Output. Apply nothing; run nothing — a reviewer has no edit or Bash tools.

## Language detection

Detect the language from the file extensions in scope and preserve that language's idioms in the rewritten code. This skill has no per-language reference files — operate from the generic procedure.

## When to Use edit_file

Use `edit_file` when:

- Multi-file batch refactoring
- Style/pattern update everywhere
- Complex prompt → many changes
- 5+ files need the same pattern
- Large files where exact replacement would be brittle

Use Built-in Edit/MultiEdit when:

- Single file, clear edit
- 2-3 targeted replacements
- Need clear diff to review/tune
- Simple rename within one file
- Straightforward single-file work

## Key Features

- **Semantic merge**: Understands code structure, not just text
- **Speed**: 10,500 tok/s vs 180 tok/s streaming
- **Accuracy**: 98% success rate on edge cases
- **dryRun**: Preview changes before applying

## Workflow

### Standard Refactoring

```
1. Define the behavior that must be preserved.
2. Map affected files with the available file/text search tools.
3. Read representative files and tests before editing.
4. Use MorphLLM `edit_file` or the batch refactoring workflow for each batch/file.
5. Batch all edits for the same file into one edit operation.
6. Verify with narrow lint/test checks, then broader checks when the batch is done.
7. Delete obsolete code exposed by the refactor.
```

For multi-file renames, say this is a batch refactor, map all occurrences before
editing, preserve behavior, and run relevant lint/tests after the rename.

### High-Stakes Changes (dryRun)

```
1. Call edit_file with dryRun: true
2. Review preview output
3. If approved, call again with dryRun: false
```

## Parameters

```
path: "/absolute/path/to/file"
code_edit: "changed lines with // ... existing code ... markers"
instruction: "brief description of changes"
dryRun: false (set true to preview)
```

## Edit Format

Use `// ... existing code ...` markers for unchanged sections:

```typescript
// ... existing code ...
function updatedFunction() {
  // new implementation
}
// ... existing code ...
```

## Common Patterns

### Batch Error Handling

```
instruction: "Add error wrapping to all repository methods"
code_edit: Shows only changed functions with context markers
```

### Import Updates

```
instruction: "Update imports from old-pkg to new-pkg"
code_edit: Shows import section with changes
```

### Multi-Location Rename

```
instruction: "Rename getUserById to findUser throughout file"
code_edit: Shows all locations with changes
```

## Output

Engineer (applied the refactor): report the preservation target, files changed,
and the lint/test verification result per touched file.

Reviewer (planned only — emit the refactor as a proposal, apply nothing):

```text
## Proposed Changes

Preservation target: <behavior that must not change>

### Change 1: <brief description>

File: `path/to/file`
Action: CREATE | MODIFY | DELETE

Code:
<changed regions with // ... existing code ... markers>

Rationale: <why this change>
```

For multi-file renames, list every occurrence mapped before the proposal so the
applier can replay it.

## Failure handling

- `edit_file` unavailable → fall back to built-in Edit/MultiEdit; warn the user that large batches may be slower
- Tests fail after a batch edit → revert the last file edit, inspect the diff, and fix the conflict before continuing
- Scope unclear (user says "refactor this") → ask: "Which files and what behavior to preserve?" before touching anything

## Tips

- Batch all edits to same file in one call
- Include enough context to locate changes precisely
- Preserve exact indentation in code_edit
- Run tests after each file to catch issues early
- Keep old public behavior stable unless the user explicitly requested behavior change
