# Release Notes

Use this reference to write or rewrite GitHub release notes. Good notes tell a
user what changed, whether it affects them, and what to do.

## Rules

- Name each release by its tag, for example `v1.4.0`. Do not use the package
  name in the title.
- Derive the content from the commits between the previous tag and this tag.
  Read the commit bodies, not only the subjects.
- Check each claim against the diff. Do not list a fix for a bug that no
  published version had.
- If a tag had no published package, say so in the next published release:
  "This release includes 1.3.1, which has no npm package."
- Use the language rules in `references/style.md`.
- Keep the generated package block and the full-changelog link at the end.

## Structure

```markdown
## Summary

<one or two sentences: the main change and why it matters>

## Fixes

- **<short label>.** <what was wrong, from the user's view>. <what happens now>.

## Changes

- <one bullet for each user-visible change>

## Upgrade

1. <command or step, imperative>
2. <restart or setup step, if needed>
```

- Leave out a section that has no content.
- Add "Upgrade" only when the user must act after the update.
- For a breaking change, write the action first and the risk second:
  "Run `tool migrate` before you start 2.0. Without it, 2.0 rejects the old
  configuration."

## Update published notes

1. Save the current title and body of each release to a local file.
2. Edit the notes, for example with `gh release edit <tag> --title <tag>
   --notes-file <file>`.
3. List the releases again and read one body to confirm the result.
