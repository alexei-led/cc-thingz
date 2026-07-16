# Gitignore Rules

## Discovery

Derive ignore rules from actual generated files and local artifacts.

Useful checks:

```bash
git status --ignored --short
git check-ignore -v <path>
git ls-files <path>
```

## Safe Patterns

Ignore:

- build outputs
- caches
- local env files
- editor files
- generated logs

Do not ignore source files, lockfiles, CI config, security config, or release artifacts unless the repo already does.

Prefer directory-specific patterns when a broad pattern would hide real source.

## Tracked Files

If a now-ignored file is tracked, ask before removing it from the index:

```bash
git rm --cached <path>
```

This must not delete the working file. Verify with `git status --short` after.
