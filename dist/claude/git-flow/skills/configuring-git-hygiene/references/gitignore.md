# Gitignore

Find what to ignore from real artifacts:

```bash
git status --ignored --short
git check-ignore -v <path>
git ls-files <path>
```

- Ignore build outputs, caches, local env files, editor files, and generated logs.
- Keep source files, lockfiles, CI config, security config, and release artifacts tracked unless the repo already ignores them.
- Use directory-specific patterns when a broad pattern would hide real source.

## Tracked files

To stop tracking a newly ignored file, run `git rm --cached <path>` after approval. It keeps the working file; confirm with `git status --short`.
