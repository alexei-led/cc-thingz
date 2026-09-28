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

Make many edits that preserve externally observable behavior. Before editing,
name the maintenance value, the behavior that must not change, and the check
that proves it; if you cannot, stop and ask.

Without write access, return proposed changes (file, change, reason) instead of
applying them. For multi-file renames, list every mapped site and mark ambiguous
ones.

Read the reference for the language being refactored; it lists that language's
caveats. Use the matching `writing-<lang>` skill for toolchain commands.

- C#: `references/csharp.md`
- Go: `references/go.md`
- Java/Kotlin: `references/java-kotlin.md`
- Python: `references/python.md`
- Rust: `references/rust.md`
- TypeScript/JavaScript: `references/typescript.md`

## Map before editing

No mapped site, no edit.

- Find every affected site with text search and language-aware rename or reference tools.
- Check non-code references when names or paths change: config, routes, DI wiring, serialization keys, CLI entries, reflection, scripts, docs.
- For renames, moves, and splits, use a code-graph tool (GitNexus, codegraph) when installed and fresh; a stale index is a gap to report, not evidence.
- If behavior is under-specified and risk is not low, add characterization tests at the public boundary first, or ask to shrink the refactor.

## Batches

- One purpose per batch: rename one concept, move one module, extract one responsibility, remove one proven duplicate, or update one repeated pattern.
- Keep mechanical changes separate from logic changes. If a behavior change turns out to be needed, stop and split it into its own fix or feature.
- Put all edits to one file in a single edit operation; preview high-stakes batches before applying.
- Keep compatibility shims or deprecations on public APIs unless the user approved a break.
- If checks fail after a batch, fix or revert that batch before starting the next.
- Delete dead code the refactor exposes. Change generated or vendored files only by regenerating from source.

Done when the relevant build/test/lint checks pass on what you changed, or you
name each check that did not run and why.

## Report

Preservation target, safety gate, mapping (tool or search, and any gaps),
changes (`path:line — change`), and each check with pass, fail, or skipped and why.

## Platform additions

No target-specific additions.
