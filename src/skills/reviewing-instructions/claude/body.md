# Instruction Review

## Claude platform additions

The host SKILL.md is canonical. This overlay only adds Claude-specific argument,
task, and aggregation behavior.

## Argument parsing

From `$ARGUMENTS`:

- first non-flag token: file path, directory path, plugin name, or omitted scope
- `--model <name>`: override model resolution
- `--team`: use parallel review agents for large scopes
- `--rerank`: use calibration anchors and pairwise comparison when comparing versions

## Task use

Use direct review for one file or one small skill folder.

Use parallel tasks only when scope contains multiple independent files or plugins.
Launch at most 3 review tasks at once. Batch deterministically by sorted path, not
by estimated difficulty.

Each task prompt must include:

- exact file list
- resolved model context or instruction to resolve it
- path to `references/scoring-rubric.md`
- path to `references/model-resolution.md`
- requirement to cite evidence for every score
- requirement to apply gates and caps before final score

## Aggregation

When task results return:

1. Verify each reviewed file was in scope.
2. Recompute caps when a task forgot them.
3. Deduplicate findings by file plus rule or dimension.
4. If two scores differ by more than 1 point, compare gates and caps first.
5. Use the lower-confidence score only as a signal; do not average incompatible scopes.
6. Put unresolved disagreements in the report as low-confidence notes.

## Rerank mode

When `$ARGUMENTS` contains `--rerank`, read `references/calibration.md`.
For two versions of a file, compare gates first, then dimensions, then final score.
If the difference is less than 0.5, report a tie.

## Web and model docs

Use web lookup for model docs only when local references are missing or the user asks
for current vendor guidance. If web access fails, use local references or generic
context and report the gap.
