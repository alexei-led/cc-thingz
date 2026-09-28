# Release Notes

The committed release section, usually the version section in `CHANGELOG.md`, is the only authored notes source.

## Content

- Explain each user-visible change and why it matters. Name affected users, behavior, or configuration when known.
- Check claims against the commits and diffs since the verified previous release. Do not claim a fix for a bug that no published version had.
- Aim for about 150 words for a patch and 250 for a minor release. These are review budgets, not truncation limits: keep migration steps, compatibility details, security notices, and known issues.
- A meaningful one-line patch note is valid. Headings, a version number, `Release VERSION`, `TODO`-only content, or a compare link alone are not release notes.
- Keep generated package or distribution metadata out of the authored summary.
- Append a full compare link only when the previous release tag is verified.
- Use the exact release tag as the release title, for example `v1.4.0`.
- Leave out empty sections.

## Structure

```markdown
## Summary

<one or two sentences about the main user-visible change>

## Changes

- <what changed and who benefits>

## Upgrade

1. <required migration action before or after upgrading>
2. <restart or setup action, when required>
```

In `Upgrade`, state the action first and the risk second:

> Run `tool migrate` before you start 2.0. Without it, 2.0 rejects the old configuration.

## Check the notes

Run the packaged checker before committing or publishing:

```bash
python3 <skill-dir>/scripts/release_notes.py check release-notes.md --budget patch
python3 <skill-dir>/scripts/release_notes.py check-changelog \
  --changelog CHANGELOG.md --version X.Y.Z --budget minor
```

It rejects placeholder-only content and reports over-budget notes as advisory. It never truncates text.
