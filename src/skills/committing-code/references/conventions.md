# Commit Conventions

Read when the repo has no recent commits to match style from, or when
the user asks for a specific format.

## Conventional Commits

Default to [Conventional Commits](https://www.conventionalcommits.org/) when
the repo uses it (check recent log or `CONTRIBUTING.md`):

```
<type>[optional scope]: <short description>

[optional body]

[optional footer(s)]
```

Common types — choose the most specific that fits:

- `feat` — a new capability visible to a user or consumer
- `fix` — a bug fix
- `refactor` — code change with no behaviour change and no new capability
- `test` — adding or changing tests only
- `docs` — documentation only
- `chore` — tooling, deps, CI, release scripts; nothing that ships
- `perf` — performance improvement
- `build` — changes to the build system or external dependencies
- `ci` — CI/CD configuration changes
- `style` — formatting only (whitespace, missing semicolons, etc.)
- `revert` — reverting a previous commit (include `Reverts: <hash>` in footer)

## Scope

Use the component, package, or domain affected. Examples: `auth`, `api`,
`cli`, `tests`, `deps`, `hooks`. Omit when the change is cross-cutting or
the repo doesn't use scopes consistently.

## Breaking changes

Add `!` after the type/scope and a `BREAKING CHANGE:` footer:

```
feat(api)!: rename /v1/users to /v2/accounts

BREAKING CHANGE: all /v1/users paths return 404. Migrate clients to /v2/accounts.
```

## Subject line rules

- Imperative mood: "add", "fix", "remove" — not "added", "fixes", "removing".
- No trailing period.
- ≤72 characters; wrap the body at 72 characters.
- Lowercase after the colon.

## Body

Add a body when:

- The _why_ behind the change is not obvious from the diff.
- The change has non-trivial side effects or migration steps.
- A bug fix includes context on the root cause.

Skip the body for mechanical changes (dependency bumps, formatting, typo fixes).

## Non-conventional repos

When the repo doesn't use Conventional Commits, match the style from the
five most recent commits. Look for:

- Capitalisation (sentence-case vs lowercase)
- Tense (imperative vs past tense)
- Length and verbosity
- Presence or absence of issue references (`fixes #42`, `closes #42`)
- Co-author or sign-off lines (`Co-authored-by:`, `Signed-off-by:`)

Replicate the pattern exactly; do not introduce a new convention.
