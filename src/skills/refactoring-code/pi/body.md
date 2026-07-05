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
