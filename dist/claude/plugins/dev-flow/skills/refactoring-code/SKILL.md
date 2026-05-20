---
allowed-tools:
- mcp__morphllm__edit_file
- mcp__morphllm__warpgrep_codebase_search
- mcp__morphllm__codebase_search
- Read
- Grep
- Glob
context: fork
description: Batch refactoring via MorphLLM edit_file. Use for "refactor across files",
  "batch rename", "update pattern everywhere", large files (500+ lines), 5+ edits
  in same file, or applying an approved architecture-deepening refactor. NOT for single-file
  targeted edits (use built-in Edit) or code review (use reviewing-code).
name: refactoring-code
user-invocable: false
---

# Fast Refactoring with MorphLLM

MorphLLM `edit_file` provides semantic code merging at 10,500+ tokens/sec with 98% accuracy. Use the MorphLLM `edit_file` / batch refactoring workflow for broad changes. Refactoring here means behavior-preserving change or architecture deepening, not cosmetic churn.

Critical rule: preserve existing behavior unless the user explicitly asks for a behavior change. State the preservation target before editing.

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
- Structural refactoring at scale
- 5+ files need same pattern

Use Built-in Edit/MultiEdit when:

- Single file, clear edit
- 2-3 targeted replacements
- Need clear diff to review/tune
- Simple rename (replace_all)
- Straightforward single-file work

## Key Features

- **Semantic merge**: Understands code structure, not just text
- **Speed**: 10,500 tok/s vs 180 tok/s streaming
- **Accuracy**: 98% success rate on edge cases
- **dryRun**: Preview changes before applying

## Architecture Deepening

When applying an approved architecture-deepening refactor, keep the seam rule (one adapter means a hypothetical seam; two adapters means a real seam — do not add interfaces without real variation) and the deletion test in mind. The module-depth vocabulary is owned upstream by `improving-codebase-architecture` (`references/LANGUAGE.md`) and `reviewing-code`; match the design agreed there and do not redefine the terms here. Read relevant `CONTEXT.md`, `CONTEXT-MAP.md`, and ADRs when present. Preserve domain names.

## Workflow

### Standard Refactoring

```
1. Map all locations before editing:
   - structural code pattern → ast-grep / sg first
   - exact text or symbol string → rg
   - semantic multi-hop flow → WarpGrep or semantic search
2. State: "Behavior must be preserved unless the user explicitly requested a behavior change."
3. Use MorphLLM `edit_file` or the batch refactoring workflow for each batch/file, grouping related edits
4. Batch all edits for the same file into one edit operation
5. Verify with lint/test
6. Delete obsolete shallow tests once deeper interface tests cover the behavior
```

For multi-file renames, say this is a batch refactor, map all occurrences before editing, use ast-grep for structural references and `rg` for plain symbol text, use the batch refactoring tool/workflow by name, preserve behavior, and run relevant lint/tests after the rename.

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

Engineer (applied the refactor): report the preservation target, files changed, and the lint/test verification result per touched file.

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

For multi-file renames, list every occurrence mapped before the proposal so the applier can replay it.

## Failure handling

- `edit_file` unavailable → fall back to built-in Edit/MultiEdit; warn the user that large batches may be slower
- Tests fail after a batch edit → revert the last file edit, inspect the diff, and fix the conflict before continuing
- Scope unclear (user says "refactor this") → ask: "Which files and what behavior to preserve?" before touching anything

## Tips

- Batch all edits to same file in one call
- Include enough context to locate changes precisely
- Preserve exact indentation in code_edit
- Use ast-grep first for structural code patterns; use WarpGrep for semantic flow
- Run tests after each file to catch issues early
- Keep old public behavior stable unless the user explicitly requested behavior change
- Prefer tests through the deepened module interface over tests of extracted helpers
