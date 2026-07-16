# C# /.NET linting

Use before changing `dotnet format`, analyzer config, warning policy, or slow
verification flow.

## Fast feedback

- Use the project's command first.
- Prefer `dotnet format` on the nearest project or solution while editing.
- For focused source edits, prefer `dotnet format <project-or-solution> --include <files>`.
- For project, solution, `.props`, or `.targets` edits, run the nearest safe project or solution target.
- Keep full-solution analyzer and test gates out of the every-turn loop unless they are the failing signal.

## Analyzer policy

- Keep nullable, analyzer, and warning-as-error policy intact unless the task is explicitly changing that policy.
- Do not disable analyzers or lower severity just to get green checks.
- Prefer fixing the warning at the source over suppression attributes or `#pragma`.
- Keep generated, vendor, and build output excluded through normal project config.

## Verification

- Use `dotnet build` when a formatting pass is not enough to prove the change.
- Run the broader project or solution command before final output when the change affects shared props, targets, package references, or public contracts.
- If lint is slow, split the hot path from the full gate; do not weaken the full gate without approval.
