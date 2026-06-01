# Refactoring Code in Pi

Refactor in small, verified batches. If behavior changes, it is not a refactor;
it is a feature wearing a fake mustache.

## Preconditions

- Understand the current behavior and test coverage.
- Identify the smallest safe batch.
- Run or add tests before broad edits when risk is non-trivial.
- Confirm before large mechanical changes across many files.

## Workflow

1. Define the refactor goal and non-goals.
2. Map all affected sites before editing with available file/text search tools.
3. Read representative files and tests.
4. Add characterization tests when behavior is under-specified.
5. Apply one coherent batch with `edit` or `write`.
6. Run narrow tests.
7. Run broader lint/type/test checks before the next batch.
8. Delete dead code introduced or exposed by the refactor.

## Safe Batches

Good batches:

- rename one public symbol and all callers
- move one function/module with tests unchanged
- remove one duplicate implementation after tests prove equivalence
- update one repeated pattern across files

Bad batches:

- rename everything while changing logic
- reorganize modules and change APIs in one pass
- add abstractions for imagined future callers
- edit generated files by hand

## Output Contract

```markdown
## Refactor Result

### Changed

- `path` — what changed

### Behavior

- preserved by <tests/checks>

### Verification

- `<command>` — pass/fail

### Follow-up

- remaining safe batches, if any
```
