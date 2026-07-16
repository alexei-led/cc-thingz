---
{"description":"Batch behavior-preserving refactors for multi-file, repeated-pattern, large-file, rename, move, extract, split, or restructure work. Use for \"refactor across files\", \"batch rename\", \"update pattern everywhere\", large files (500+ lines), or 5+ coordinated edits in one file. NOT for single targeted edits, behavior changes or bug fixes (use fixing-code), test-only refactors (use improving-tests), code review (use reviewing-code), or architecture redesign (use architecture-design/review).","name":"refactoring-code"}
---
<!-- Pi platform guidance -->
<!-- Use installed Pi tool names exactly. Installed extensions may add toolsets such as Task*, Monitor*, and Loop*; use the visible tool names exactly and do not translate them to Claude syntax. -->
<!-- Prefer Task* over `todo` when task-tracking tools are available; `todo` is the cc-thingz fallback. Prefer MonitorCreate for long-running or background commands and LoopCreate for scheduled or event-driven follow-up instead of Bash sleep/poll loops. -->
<!-- Use subagent for delegated work. Use wait to block on async subagent runs only when no independent work remains. -->
<!-- Use ctx7 or npx ctx7@latest through bash when Context7 documentation lookup is required. -->

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
