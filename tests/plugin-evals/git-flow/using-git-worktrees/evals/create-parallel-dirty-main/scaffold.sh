#!/usr/bin/env bash
# Sets up a small git repo in the sandbox cwd on main, with an uncommitted
# README change — mirrors "I'm mid-review on main, start isolated work
# elsewhere without touching it."
set -euo pipefail

git init -q .
git config user.email "eval@example.com"
git config user.name "Eval Runner"
git symbolic-ref HEAD refs/heads/main

printf '# shop\n\nOnline shop app.\n' >README.md
git add README.md
git commit -q -m "initial commit"

# Leave an uncommitted change in the main worktree, as in the prompt.
printf '\n## Status\n\nIn progress.\n' >>README.md
