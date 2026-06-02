# Phase 5: Apply Fixes

Load and run this phase only when `--fix` is in `$ARGUMENTS`. Without `--fix`, the
skill stops after Phase 4 (review only — the user applies fixes).

If specific fix actions were not pre-approved, use `AskUserQuestion`. Ask one question at a time:

- **Action** — Apply fixes from the review? Options: Fix all errors / Fix errors + warnings / Show diffs only / Skip

Apply only approved fixes. Confirm before deleting files, removing hooks, broad rewrites, or changing permissions:

1. **CLAUDE.md**: Remove flagged lines, move content to skills/hooks
2. **Skills**: Add missing `context: fork`, trim tool lists, fix descriptions
3. **Agents**: Add scope boundaries, output format sections
4. **Hooks**: Fix exit codes, event assignments

After each fix, show the diff. Do NOT make changes beyond what was flagged.

## Post-fix verification

After all fixes are applied, re-check modified components against the rules that triggered the fix. Confirm each finding is resolved. Report any regressions.
