---
{"description":"Batch behavior-preserving refactors for multi-file, repeated-pattern, large-file, rename, move, extract, split, or restructure work. Use for \"refactor across files\", \"batch rename\", \"update pattern everywhere\", large files (500+ lines), or 5+ coordinated edits in one file. NOT for single targeted edits, behavior changes or bug fixes (use fixing-code), test-only refactors (use improving-tests), code review (use reviewing-code), or architecture redesign (use architecture-design/review).","name":"refactoring-code"}
---
<!-- Pi platform guidance -->
<!-- Use installed Pi tool names exactly, including extension toolsets such as Task*, Monitor*, and Loop*. -->
<!-- When available, track work with Task* (`todo` is the fallback), run long or background commands with MonitorCreate, and schedule follow-up with LoopCreate instead of sleep/poll loops. -->

# Batch Refactoring

Follow the base skill. This Pi overlay only defines tool use and execution details.

## Pi tool rules

- Pi has no tool-level read-only enforcement; follow the active agent's role
  directive (`engineer` applies one batch, `reviewer` proposes only) rather
  than inferring the role from tool availability.
- Use `bash` (`rg`, `fd`, `git grep`) to map affected sites; Pi has no
  dedicated grep/glob tool.
- Use `edit` for existing files and `write` only for new files.
- Prefer installed Task* tools to track multi-batch refactors across steps; fall back to `todo` when that task toolset is unavailable.
- Use `ask_user_question` when scope, preservation target, or safety gate is unclear.

## Output on Pi

Use the base skill's Engineer and Reviewer output contracts exactly, unmodified.
