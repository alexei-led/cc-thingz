#!/usr/bin/env bash
# Sets up a git repo with an existing worktree for a branch the user says
# was already squash-merged on GitHub — and no `gh` on PATH to confirm it.
set -euo pipefail

git init -q .
git config user.email "eval@example.com"
git config user.name "Eval Runner"
git symbolic-ref HEAD refs/heads/main

printf '# shop\n\nOnline shop app.\n' >README.md
git add README.md
git commit -q -m "initial commit"

git worktree add -q -b feature/auth ../repo.worktrees/feature-auth >/dev/null

# `gh` should already be absent from the eval sandbox's PATH; the case's
# `execution.env` clears it explicitly so the premise holds regardless of
# the host image.
