---
{"description":"Batch behavior-preserving refactors for multi-file, repeated-pattern, large-file, rename, move, extract, split, or restructure work. Use for \"refactor across files\", \"batch rename\", \"update pattern everywhere\", large files (500+ lines), or 5+ coordinated edits in one file. NOT for single targeted edits, behavior changes or bug fixes (use fixing-code), test-only refactors (use improving-tests), code review (use reviewing-code), or architecture redesign (use architecture-design/review).","name":"refactoring-code"}
---
<!-- Pi platform guidance -->
<!-- Use installed Pi tool names exactly. Installed extensions may add toolsets such as Task*, Monitor*, and Loop*; use the visible tool names exactly and do not translate them to Claude syntax. -->
<!-- Prefer Task* over `todo` when task-tracking tools are available; `todo` is the cc-thingz fallback. Prefer MonitorCreate for long-running or background commands and LoopCreate for scheduled or event-driven follow-up instead of Bash sleep/poll loops. -->
<!-- Use subagent for authorized delegation. Ordinary async subagents notify the parent natively; yield instead of polling or calling bg_wait merely because a child is active. Use blocking bg_wait only for provider, detached, or other background work without a native notification when a required same-turn result is needed. -->
<!-- Current pi-subagents uses one model per launch; do not configure fallbackModels. A different model requires an explicit new launch after inspecting the failed run and partial work. Use the owning workflow/controller for retries. -->
<!-- Use ctx7 or npx ctx7@latest through bash when Context7 documentation lookup is required. -->


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
- Run the safety gate after each batch. If it fails, fix or revert that batch before starting the next.
- Delete dead code the refactor exposes. Change generated or vendored files only by regenerating from source.

Done when the relevant build/test/lint checks pass on what you changed, or you
name each check that did not run and why.

## Report

Preservation target, safety gate, mapping (tool or search, and any gaps),
changes (`path:line — change`), and each check with pass, fail, or skipped and why.

## Platform additions

### Pi tools

- Pi does not enforce read-only tools. Follow the active agent's role directive (`engineer` applies one batch, `reviewer` proposes only) instead of inferring the role from which tools exist.
- Map sites with `bash` (`rg`, `fd`, `git grep`); Pi has no dedicated grep or glob tool.
- Use `edit` for existing files and `write` only for new files.
- Track multi-batch refactors with installed Task* tools, or `todo` when they are unavailable.
- Ask with `ask_user_question` when the scope, preservation target, or safety gate is unclear.
