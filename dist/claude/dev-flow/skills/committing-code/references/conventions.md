# Commit Conventions

Read when the repo has no recent commits to match, or the user asks for a format.

- Use [Conventional Commits](https://www.conventionalcommits.org/) when recent
  history or `CONTRIBUTING.md` uses it. Pick the most specific type; use a scope
  only when the repo uses scopes consistently.
- Mark a breaking change with `!` after the type or scope and a
  `BREAKING CHANGE:` footer that names the migration.
- Subject: imperative, no trailing period, at most 72 characters. Wrap the body
  at 72 characters.
- Add a body only when the reason, a side effect, a migration, or a root cause is
  not obvious from the diff.
- In a repo without Conventional Commits, copy the style of the last five
  commits: capitalization, tense, length, issue references (`fixes #42`), and
  trailers such as `Co-authored-by:` or `Signed-off-by:`. Do not introduce a new
  convention.
