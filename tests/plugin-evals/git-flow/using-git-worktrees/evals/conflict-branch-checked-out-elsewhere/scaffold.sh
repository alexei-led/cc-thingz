#!/usr/bin/env bash
# main is clean, but the branch the user is about to ask for is already
# checked out in another worktree.
set -euo pipefail

git init -q .
git config user.email "eval@example.com"
git config user.name "Eval Runner"
git symbolic-ref HEAD refs/heads/main

printf '# shop\n\nOnline shop app.\n' >README.md
git add README.md
git commit -q -m "initial commit"

git worktree add -q -b feature/payments ../repo.worktrees/feature-payments >/dev/null
