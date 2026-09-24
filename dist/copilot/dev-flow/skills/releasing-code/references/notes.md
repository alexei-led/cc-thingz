# Release Notes

Use the committed release section as the only authored notes source. For cc-thingz that source is the version section in `CHANGELOG.md`; the release workflow renders it. Do not maintain a second body in the hosting service.

## Content

- Explain the user-visible change and why it matters. Name affected users, behavior, or configuration when known.
- Check claims against the commits and diffs since the verified previous release. Read commit bodies, not only subjects. Do not claim a fix for a bug that was not present in a published version.
- Keep notes concise: about 150 words for a patch and 250 for a minor release. These are review budgets, not truncation limits. Preserve required migration steps, compatibility details, security notices, and known issues.
- A meaningful one-line patch note is valid. Headings, a version number, `Release VERSION`, `TODO`-only content, or a compare link alone are not release notes.
- Do not mix generated package/distribution metadata into the authored change summary. The cc-thingz renderer appends those sections separately.
- Append a full compare link only when the previous release tag is verified. Do not use an unverified or future tag.
- Use the exact release tag as the hosting release title, for example `v1.4.0`.
- Leave out sections without content. Include `Upgrade` for every declared breaking change, with the required action and consequence of skipping it.

## Suggested structure

```markdown
## Summary

<one or two sentences about the main user-visible change>

## Changes

- <what changed and who benefits>

## Upgrade

1. <required migration action before or after upgrading>
2. <restart or setup action, when required>
```

For a breaking change, state the action first and the risk second:

> Run `tool migrate` before you start 2.0. Without it, 2.0 rejects the old configuration.

## Check the notes

Run the packaged checker before committing or publishing:

```bash
python3 <skill-dir>/scripts/release_notes.py check release-notes.md --budget patch
python3 <skill-dir>/scripts/release_notes.py check-changelog \
  --changelog CHANGELOG.md --version 6.13.0 --budget minor
```

The checker rejects placeholder-only content and reports over-budget notes as an advisory. It never truncates text.
